import os
import json
import random
import base64
import requests
import textwrap
import time
from PIL import Image, ImageDraw, ImageFont
import logging
from openai import OpenAI
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from json import JSONDecodeError
import re


def load_env_variables(env_file: str = './.env') -> None:
    """
    Load environment variables from a file.
    Each line in the file should be in the format KEY=VALUE
    """
    env_file = os.path.expanduser(env_file)

    with open(env_file, 'r') as f:
        for line in f:
            if '=' in line:
                key, value = line.strip().split('=', 1)
                key = key.strip()
                value = value.strip()
                # Remove quotes if present
                if value[0] == value[-1] and value.startswith(("'", '"')):
                    value = value[1:-1]
                os.environ[key] = value

class ModernChatGPT:
    def __init__(self, system_prompt: str = "", model: str = "gpt-3.5-turbo-0125"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_TOKEN"))
        self.system = system_prompt
        self.messages = []
        if self.system:
            self.messages.append({"role": "system", "content": system_prompt})
        self.model = model

    def __call__(self, message: str) -> str:
        self.messages.append({"role": "user", "content": message})
        result = self.execute()
        self.messages.append({"role": "assistant", "content": result})
        return result

    def execute(self) -> str:
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages
            )
            return completion.choices[0].message.content
        except Exception as e:
            logging.error(f"OpenAI API error: {str(e)}")
            raise

class InstagramAPI:
    def __init__(self, user_id: str, access_token: str):
        self.user_id = user_id
        self.access_token = access_token
        self.api_version = "v21.0"
        self.base_url = "https://graph.facebook.com"

    def create_media_container(self, media_urls: List[str], media_type: str = "IMAGE", caption: str = None) -> str:
        """Creates a media container for Instagram post/story
        
        Args:
            media_urls: List of image URLs
            media_type: Either 'IMAGE' or 'CAROUSEL_ALBUM'
            caption: Optional caption for the post
        
        Returns:
            str: Container ID for publishing
        """
        endpoint = f"{self.base_url}/{self.api_version}/{self.user_id}/media"
        
        try:
            if media_type == "CAROUSEL_ALBUM":
                # Step 1: Create container for each image
                container_ids = []
                for url in media_urls:
                    params = {
                        "media_type": "IMAGE",
                        "image_url": url,
                        "access_token": self.access_token
                    }
                    response = requests.post(endpoint, params=params)
                    response.raise_for_status()
                    container_ids.append(response.json()["id"])
                
                # Step 2: Create carousel container
                params = {
                    "media_type": "CAROUSEL",
                    "children": ",".join(container_ids),
                    "access_token": self.access_token
                }
            else:
                # Single image container
                params = {
                    "media_type": media_type,
                    "image_url": media_urls[0],
                    "access_token": self.access_token
                }
            
            if caption:
                params["caption"] = caption
                
            response = requests.post(endpoint, params=params)
            response.raise_for_status()
            return response.json()["id"]
            
        except requests.exceptions.HTTPError as err:
            print(f"HTTP error occurred: {err} - Response: {response.text}")
            raise
        except Exception as err:
            print(f"Error creating media container: {err}")
            raise

    def publish_media(self, creation_id: str) -> Dict:
        """Publishes the media to Instagram"""
        endpoint = f"{self.base_url}/{self.api_version}/{self.user_id}/media_publish"
        params = {
            "creation_id": creation_id,
            "access_token": self.access_token
        }
            
        response = requests.post(endpoint, params=params)
        response.raise_for_status()
        return response.json()




class ContentGenerator:
    def __init__(self, config: Dict):
        self.config = config
        self.imgur_client_id = config["imgur_client_id"]
        self.setup_image_generation()

    def setup_image_generation(self):
        """Setup image generation parameters."""
        # Templates
        self.story_template_path = "./images/templates/stories_template.png"  # Path to the story template
        self.post_template_path = "./images/templates/post_template.png"  # Path to the post slide template
        self.disclaimer_text = "*This content is generated by an AI and may not be entirely accurate or reliable."

        # Fonts and styles
        self.fonts = {
            "bold": ImageFont.truetype("fonts/RobotoSlab-Bold.ttf", size=50),
            "normal": ImageFont.truetype("fonts/FiraSans-Medium.ttf", size=35),
            "italic": ImageFont.truetype("fonts/FiraSans-Italic.ttf", size=30),
            "disclaimer": ImageFont.truetype("fonts/FiraSans-Medium.ttf", size=25)
        }
        self.white_color = (255, 255, 255)  # Default font color (white)
        self.black_color = (0, 0, 0)  # Title color (black)

    def generate_story_content(self, content: Dict) -> str:
        """
        Generates a single Instagram story image using the story template.
        """
        content["disclaimer"] = self.disclaimer_text
        timestamp = datetime.now().strftime("%Y-%m-%d")
        output_path = f"images/contents/stories/{timestamp}/story_{content['name'].replace(' ', '_').replace(':', '_').replace('?', '_').replace('!', '_').replace(',', '_').replace('/', '_')}"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Break line if the title has a colon
        if ":" in content["name"]:
            content["name"] = content["name"].replace(":", ":\n")

        output_path += ".png"
        img = self._generate_template_image(
            content,
            template_path=self.story_template_path,
            positions={
                "name": (50, 150, 1030, 750),  # Title (centered in post)
                "description": (50, 700, 1030, 750),  # Description (centered in post)
                "example": (50, 1300, 1030, 750),  # Example (centered in post)
                "disclaimer": (50, 1800, 1030, 750)  # Disclaimer (centered in post)
            },
            output_path=output_path
        )

        return [output_path]

    def generate_post_content(self, content: Dict) -> List[str]:
        """
        Generates a carousel post with three slides using the post template.
        Each slide will include a different part of the content: title, description, and example.
        """
        # Break line if the title has a colon
        timestamp = datetime.now().strftime("%Y-%m-%d")
        slide_path = f"images/contents/posts/{timestamp}/post_{content['name'].replace(' ', '_').replace(':', '_').replace('?', '_').replace('!', '_').replace(',', '_').replace('/', '_')}"
        os.makedirs(os.path.dirname(slide_path), exist_ok=True)

        if ":" in content["name"]:
            content["name"] = content["name"].replace(":", ":\n")

        slides_content = [
            {"name": content["name"]},
            {"description": content["description"]},
            {"example": content["example"]},
            {"disclaimer": self.disclaimer_text}
        ]
        
        output_paths = []
        for i, slide_content in enumerate(slides_content):
            output_path = f"{slide_path}_slide_{i}.png"
            img = self._generate_template_image(
                slide_content,
                template_path=self.post_template_path,
                positions={
                    "name": (50, 350, 1030, 750),  # Title (centered in post)
                    "description": (50, 350, 1030, 750),  # Description (centered in post)
                    "example": (50, 350, 1030, 750),  # Example (centered in post)
                    "disclaimer": (50, 350, 1030, 750)  # Disclaimer (centered in post)
                },
                output_path=output_path
            )            
            output_paths.append(output_path)
        return output_paths

    def _generate_template_image(
        self, content: Dict, template_path: str, positions: Dict[str, tuple], output_path: str
    ) -> str:
        """
        Generates an image by placing content on a given template.
        """
        # Load template
        img = Image.open(template_path).convert("RGBA")
        draw = ImageDraw.Draw(img)

        # Draw content at specified positions
        for key, box in positions.items():
            if key in content:
                if key == "name":
                    font = self.fonts["bold"]
                    wrap_width = 30
                elif key == "example":
                    font = self.fonts["italic"]
                    wrap_width = 40
                elif key == "disclaimer":
                    font = self.fonts["disclaimer"]
                    wrap_width = 50
                else:
                    font = self.fonts["normal"]
                    wrap_width = 40

                if template_path == self.story_template_path:
                    color = self.white_color if key == "name" or key == "disclaimer" else self.black_color
                else:
                    color = self.black_color 

                # For posts, center the text vertically and horizontally
                if template_path == self.post_template_path:
                    self._draw_text_in_box(draw, content[key], font, box, color, wrap_width, center_text=True)
                else:
                    self._draw_text_in_box(draw, content[key], font, box, color, wrap_width)

        # Save and return the image
        img.save(output_path, optimize=True, quality=95)

        return img

    def _draw_text_in_box(self, draw, text: str, font: ImageFont.FreeTypeFont, box: tuple, color: tuple, wrap_width: int = 35, center_text=False):
        """
        Draws text wrapped and centered inside a given bounding box.
        Breaks lines and positions them appropriately.
        """
        # Get the bounding box for the text
        lines = textwrap.wrap(text, width=wrap_width, break_long_words=False)  # Wrap text to fit width
        nl_acc = 0  # Vertical accumulator for the line height

        # Calculate the total height of the wrapped text
        total_text_height = 0
        for line in lines:
            _, _, line_width, line_height = draw.textbbox((0, 0), line, font=font)
            total_text_height += line_height + 5  # Adding space between lines

        # If center_text is True, adjust the starting y-position for vertical centering
        y_offset = box[1]
        if center_text:
            box_height = box[3] - box[1]
            y_offset = box[1] + (box_height - total_text_height) // 2

        # Draw each line of text
        for line in lines:
            _, _, line_width, line_height = draw.textbbox((0, 0), line, font=font)

            # Calculate horizontal center position
            box_width = box[2] - box[0]
            x = box[0] + (box_width - line_width) / 2

            # Draw the text at the calculated position
            draw.text((x, y_offset + nl_acc), line, font=font, fill=color)

            # Accumulate line height to adjust vertical position for the next line
            nl_acc += line_height + 5  # Add space between lines


    def upload_to_imgur(self, image_path: str) -> str:
        """Uploads an image to Imgur and returns the URL."""
        headers = {"Authorization": f"Client-ID {self.imgur_client_id}"}
        with open(image_path, "rb") as file:
            image_data = base64.b64encode(file.read()).decode()
        response = requests.post(
            "https://api.imgur.com/3/image",
            headers=headers,
            data={"image": image_data}
        )
        response.raise_for_status()
        return response.json()["data"]["link"]


def extract_json_from_text(text: str) -> str:
    """Extract JSON content from text, handling cases where there might be additional text."""
    # Try to find JSON-like content between curly braces
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        return json_match.group(0)
    return text

def generate_content_for_topic(chat_gpt: ModernChatGPT, topic: str) -> Dict:
    """Generate and validate content for a topic with retries."""
    prompt = f"""
        Explain {topic} in a nutshell. 
        IMPORTANT: Your response must be ONLY a valid JSON object with exactly these fields:
        {{
            "name": "{topic}",
            "description": "Brief clear explanation (max 500 chars)",
            "example": "Practical example (max 500 chars)"
        }}
        Do not include any other text, only the JSON object.
    """
    
    prompt = f"""
        Explain this entrepreneurship concept: {topic}
        IMPORTANT: Your response must be ONLY a valid JSON object with exactly these fields:
        {{
            "name": "{topic}",
            "description": "Clear, actionable explanation focusing on practical implementation for entrepreneurs (max 500 chars)",
            "example": "Real-world business example or case study showing successful implementation (max 500 chars)"
        }}
        Make the content practical and implementation-focused. Include specific tips or steps when relevant.
        Do not include any other text, only the JSON object.
    """

    # Prompt template for generating content about specific topics
    topic_prompt = f"""
    Explain this startup concept as if advising a YC founder: {topic}
    IMPORTANT: Your response must be ONLY a valid JSON object with exactly these fields:
    {{
        "name": "{topic}",
        "description": "Direct, no-BS explanation with concrete metrics or actions to focus on. Reference YC's experience when relevant. Focus on common mistakes and counter-intuitive truths. (max 500 chars)",
        "example": "Specific case study from a YC company or well-known startup showing both what worked and what didn't work initially. Include real metrics/numbers when possible. (max 500 chars)"
    }}
    Remember: 1) Focus on measurable actions and results 2) Include specific metrics or benchmarks 3) Address common misconceptions
    Do not include any other text, only the JSON object.
    """

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = chat_gpt(topic_prompt)
            # Try to extract JSON if there's surrounding text
            json_str = extract_json_from_text(response)
            content = json.loads(json_str)

            # Validate required fields
            required_fields = {"name", "description", "example"}
            if not all(field in content for field in required_fields):
                raise ValueError(f"Missing required fields. Got: {list(content.keys())}")
            
            # Truncate long fields
            content["description"] = content["description"][:500]
            content["example"] = content["example"][:500]
            return content
            
        except JSONDecodeError as e:
            logging.warning(f"Attempt {attempt + 1}/{max_retries} failed to parse JSON for {topic}: {str(e)}")
            if attempt == max_retries - 1:
                raise
            time.sleep(2)  # Wait before retry
            
        except Exception as e:
            logging.error(f"Unexpected error generating content for {topic}: {str(e)}")
            raise

def main():
    
    os.makedirs("images", exist_ok=True)
    os.makedirs("fonts", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    # Setup logging
    logging.basicConfig(
        filename=f"./logs/content_generator_{datetime.now().strftime('%Y%m%d')}.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )

    # Load environment variables
    try:
        load_env_variables()
        logging.info("Successfully loaded environment variables")
    except Exception as e:
        logging.error(f"Error loading environment variables: {str(e)}")
        raise

    # Load configuration from environment
    config = {
        "imgur_client_id": os.getenv("IMGUR_CLIENT_ID"),
        "instagram_user_id": os.getenv("INSTA_USER_ID"),
        "instagram_access_token": os.getenv("INSTA_ACCESS_TOKEN")
    }

    # Validate required environment variables
    required_vars = ["OPENAI_TOKEN", "IMGUR_CLIENT_ID", "INSTA_USER_ID", "INSTA_ACCESS_TOKEN"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    try:
        # Initialize components
        chat_gpt = ModernChatGPT(
            #system="You are a University professor and researcher in Artificial Intelligence. Your task is to generate educational content for Instagram posts.",
            #system="You are a successful entrepreneur and business consultant with expertise in startups and business development. Your task is to generate practical, actionable content for aspiring entrepreneurs and startup founders. Focus on real-world applications, specific strategies, and proven methodologies.",
            system_prompt = """You are Paul Graham, Y Combinator co-founder and startup expert. Your task is to generate content that reflects YC's core philosophy: 
            'Make something people want. Talk to users. Ship fast. Grow fast.' Focus on counter-intuitive truths about startups that founders often miss. 
            Share insights drawn from YC's experience with thousands of startups, emphasizing metrics-driven growth, rapid iteration, and intense user focus. 
            Keep advice practical and actionable, avoiding feel-good startup platitudes."""
        )
        instagram = InstagramAPI(
            user_id=config["instagram_user_id"],
            access_token=config["instagram_access_token"]
        )
        content_gen = ContentGenerator(config)

        # Generate topics
        topics_generation_prompt = """
Generate 200 specific startup topics that address key challenges faced by Y Combinator founders, categorized according to YC's core principles, ensuring balanced coverage across the following areas, each comprising 25% of the topics:
1) Building Something People Want: Focus on user research, problem validation, MVP definition, product iteration, usage metrics, retention measurement, feature prioritization, and customer feedback loops.
2) Rapid Growth & Scaling: Cover growth rate metrics, customer acquisition channels, sales optimization, market expansion, viral coefficients, churn reduction, revenue scaling models, and unit economics.
3) Founder & Team Execution: Address co-founder dynamics, early hiring decisions, equity structure, remote management, company culture, decision-making frameworks, performance measurement, and organizational design.
4) Fundraising & Runway: Include pitch deck creation, investor tactics, term sheet negotiation, cap table management, burn rate optimization, valuation methods, due diligence preparation, and follow-on funding strategies.
Output the topics in JSON format as follows: { "topics": ["Topic 1", "Topic 2", ..., "Topic 200"] }. Each topic should be specific and actionable with measurable outcomes. Avoid generic advice or duplicate topics. Provide only the JSON output without any additional text or explanations.
        """

        topics_response = chat_gpt(topics_generation_prompt)

        logging.info(f"Generated topics: {topics_response}")
        
        # Extract topics from response
        topics = json.loads(topics_response)["topics"]
        logging.info(f"Extracted topics: {topics}")
        print(f"Extracted topics: {topics}")
        # Process each topic
        for i, topic in enumerate(topics):
            try:
                logging.info(f"Processing topic {i+1}: {topic}")
                
                # Generate content with improved error handling
                content = generate_content_for_topic(chat_gpt, topic)
                logging.info(f"Generated content for {topic}: {content}")
                
                # Generate and upload image
                post_images_path = content_gen.generate_post_content(content)
                logging.info(f"Generated image for: {topic} at {post_images_path}")
                story_image_path = content_gen.generate_story_content(content)
                logging.info(f"Generated image for: {topic} at {story_image_path}")

                post_image_urls = [content_gen.upload_to_imgur(path) for path in post_images_path]
                logging.info(f"Uploaded images for: {topic} at {post_image_urls}")
                story_image_urls = [content_gen.upload_to_imgur(path) for path in story_image_path]
                logging.info(f"Uploaded image for: {topic} at {story_image_urls}")

                # Post to Instagram
                post_creation_id = instagram.create_media_container(post_image_urls, media_type="CAROUSEL_ALBUM", caption=f"{content['name']}\n\n{content['description']}\n\n{content['example']}\n\n#Enterpreneurship #YCombinator #YC #Startup")
                instagram.publish_media(post_creation_id)
                logging.info(f"Published post for: {topic}")
                story_creation_id = instagram.create_media_container(story_image_urls, media_type="STORIES")
                instagram.publish_media(story_creation_id)
                logging.info(f"Published story for: {topic}")

                # Wait 1440 minutes (24 hours) before posting the next topic
                time.sleep((1440 + random.randint(-5, 5)) * 60)
                
            except Exception as e:
                logging.error(f"Error processing topic {topic}: {str(e)}")
                continue

    except Exception as e:
        logging.error(f"Fatal error in main execution: {str(e)}")

if __name__ == "__main__":
    main()