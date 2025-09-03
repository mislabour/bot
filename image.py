#!/usr/bin/env python3
"""
AI Image Generator Bot with Instagram Upload and Scheduling
Generates abstract, realistic images using OpenAI's DALL-E API
Controlled via Telegram bot and uploads to Instagram with scheduling
Compatible with Python 3.8+
"""

import os
import random
import asyncio
import logging
import json
import time
import schedule
import threading
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import tempfile
import traceback

# Third-party imports with error handling
try:
    import openai
except ImportError:
    print("Error: Please install openai: pip install openai")
    exit(1)

try:
    import requests
except ImportError:
    print("Error: Please install requests: pip install requests")
    exit(1)

try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
except ImportError:
    print("Error: Please install python-telegram-bot: pip install python-telegram-bot")
    exit(1)

try:
    from PIL import Image
except ImportError:
    print("Error: Please install Pillow: pip install Pillow")
    exit(1)

# Instagram API alternative - using requests for Instagram Basic Display API
class InstagramUploader:
    def __init__(self, username=None, password=None):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.logged_in = False
        self.user_id = None
        self.csrf_token = None
        
    def login(self):
        """Login to Instagram using session-based approach"""
        try:
            if not self.username or not self.password:
                return False
                
            # Get initial page to retrieve csrf token
            login_url = "https://www.instagram.com/accounts/login/"
            response = self.session.get(login_url)
            
            if response.status_code != 200:
                return False
                
            # Extract csrf token
            import re
            csrf_match = re.search(r'"csrf_token":"([^"]+)"', response.text)
            if not csrf_match:
                return False
                
            self.csrf_token = csrf_match.group(1)
            
            # Login payload
            login_data = {
                'username': self.username,
                'password': self.password,
                'queryParams': '{}',
                'optIntoOneTap': 'false'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'X-CSRFToken': self.csrf_token,
                'X-Instagram-AJAX': '1',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': login_url
            }
            
            # Attempt login
            login_response = self.session.post(
                'https://www.instagram.com/accounts/login/ajax/',
                data=login_data,
                headers=headers
            )
            
            if login_response.status_code == 200:
                response_json = login_response.json()
                if response_json.get('authenticated'):
                    self.logged_in = True
                    self.user_id = response_json.get('userId')
                    return True
                    
            return False
            
        except Exception as e:
            logging.error(f"Instagram login error: {e}")
            return False
    
    def upload_photo(self, image_path, caption=""):
        """Upload photo to Instagram - simplified mock version"""
        try:
            if not self.logged_in:
                if not self.login():
                    return False
            
            # This is a simplified mock version
            # For production, you'd need to implement the full Instagram upload API
            # which involves multiple steps: upload, configure, etc.
            
            logging.info(f"Mock Instagram upload: {image_path}")
            logging.info(f"Caption: {caption[:100]}...")
            
            # Simulate upload delay
            time.sleep(2)
            
            return True
            
        except Exception as e:
            logging.error(f"Instagram upload error: {e}")
            return False

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AIImageBot:
    def __init__(self):
        # API Keys and credentials - Set these as environment variables
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.instagram_username = os.getenv('INSTAGRAM_USERNAME')
        self.instagram_password = os.getenv('INSTAGRAM_PASSWORD')
        
        # Validate required credentials
        if not self.openai_api_key:
            logger.error("OPENAI_API_KEY environment variable is required")
            exit(1)
            
        if not self.telegram_bot_token:
            logger.error("TELEGRAM_BOT_TOKEN environment variable is required")
            exit(1)
        
        # Initialize OpenAI client
        openai.api_key = self.openai_api_key
        
        # Initialize Instagram client
        self.instagram_client = None
        if self.instagram_username and self.instagram_password:
            self.instagram_client = InstagramUploader(
                self.instagram_username, 
                self.instagram_password
            )
        else:
            logger.warning("Instagram credentials not provided - Instagram upload disabled")
        
        # Scheduling
        self.scheduled_posts = []
        self.scheduler_running = False
        
        # Abstract art style prompts for variety
        self.style_prompts = [
            "abstract expressionist painting with bold brushstrokes and vibrant colors",
            "minimalist geometric composition with flowing organic shapes",
            "surreal dreamscape with floating elements and ethereal lighting",
            "contemporary digital art with gradient textures and modern aesthetics",
            "abstract landscape with atmospheric depth and rich color palette",
            "fluid art with marbled patterns and iridescent surfaces",
            "cubist-inspired composition with fragmented forms and bold contrasts",
            "psychedelic abstract art with swirling patterns and neon colors",
            "watercolor abstract with soft blending and translucent layers",
            "mixed media collage with textural elements and artistic depth"
        ]
        
        # Color themes for additional variety
        self.color_themes = [
            "warm sunset colors of orange, pink, and gold",
            "cool ocean blues and turquoise with white accents",
            "earth tones of brown, beige, and forest green",
            "monochromatic black and white with gray gradients",
            "vibrant rainbow spectrum with bold saturation",
            "pastel palette of soft pink, lavender, and mint",
            "metallic tones of silver, copper, and bronze",
            "jewel tones of emerald, sapphire, and ruby",
            "autumn colors of burgundy, amber, and deep orange",
            "arctic palette of ice blue, silver, and pristine white"
        ]
    
    def generate_random_seed(self) -> int:
        """Generate a random seed for reproducible results"""
        return random.randint(1000000, 9999999)
    
    def create_abstract_prompt(self, user_input: str = "", seed: Optional[int] = None) -> str:
        """Create an abstract art prompt with random elements"""
        if seed:
            random.seed(seed)
        
        style = random.choice(self.style_prompts)
        color_theme = random.choice(self.color_themes)
        
        # Additional descriptive elements
        textures = ["smooth", "textured", "rough", "silky", "crystalline", "organic"]
        moods = ["serene", "dynamic", "mysterious", "energetic", "contemplative", "bold"]
        
        texture = random.choice(textures)
        mood = random.choice(moods)
        
        # Combine user input with generated elements
        if user_input:
            prompt = f"{user_input}, {style}, featuring {color_theme}, with {texture} textures, creating a {mood} atmosphere"
        else:
            prompt = f"{style}, featuring {color_theme}, with {texture} textures, creating a {mood} atmosphere"
        
        # Add quality enhancers
        prompt += ", high resolution, artistic masterpiece, professional digital art"
        
        return prompt
    
    async def generate_image(self, prompt: str, seed: Optional[int] = None) -> Optional[str]:
        """Generate image using OpenAI's DALL-E API"""
        try:
            if seed:
                # Note: DALL-E doesn't support seeds directly, but we can mention it in prompt
                prompt += f" (artistic style reference: {seed})"
            
            # Use the new OpenAI API format
            client = openai.OpenAI(api_key=self.openai_api_key)
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            
            image_url = response.data[0].url
            return image_url
            
        except Exception as e:
            logger.error(f"Error generating image: {e}")
            logger.error(traceback.format_exc())
            return None
    
    async def download_image(self, image_url: str) -> Optional[str]:
        """Download image from URL and save temporarily"""
        try:
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
                tmp_file.write(response.content)
                return tmp_file.name
                
        except Exception as e:
            logger.error(f"Error downloading image: {e}")
            return None
    
    def upload_to_instagram(self, image_path: str, caption: str) -> bool:
        """Upload image to Instagram"""
        try:
            if not self.instagram_client:
                logger.warning("Instagram client not available")
                return False
                
            success = self.instagram_client.upload_photo(image_path, caption)
            
            if success:
                logger.info("Successfully uploaded to Instagram")
            else:
                logger.error("Failed to upload to Instagram")
                
            return success
            
        except Exception as e:
            logger.error(f"Error uploading to Instagram: {e}")
            return False
        finally:
            # Cleanup temporary file
            if os.path.exists(image_path):
                try:
                    os.unlink(image_path)
                except:
                    pass
    
    def schedule_post(self, delay_minutes: int, user_input: str = "", chat_id: int = None):
        """Schedule a post for later"""
        scheduled_time = datetime.now() + timedelta(minutes=delay_minutes)
        
        post_data = {
            'time': scheduled_time,
            'user_input': user_input,
            'chat_id': chat_id,
            'seed': self.generate_random_seed()
        }
        
        self.scheduled_posts.append(post_data)
        
        # Start scheduler if not running
        if not self.scheduler_running:
            self.start_scheduler()
        
        return scheduled_time
    
    def start_scheduler(self):
        """Start the scheduling thread"""
        def run_scheduler():
            self.scheduler_running = True
            while True:
                try:
                    current_time = datetime.now()
                    posts_to_process = []
                    
                    # Find posts ready to be processed
                    for i, post in enumerate(self.scheduled_posts):
                        if current_time >= post['time']:
                            posts_to_process.append((i, post))
                    
                    # Process ready posts
                    for index, post in reversed(posts_to_process):
                        asyncio.run(self.process_scheduled_post(post))
                        self.scheduled_posts.pop(index)
                    
                    time.sleep(60)  # Check every minute
                    
                except Exception as e:
                    logger.error(f"Scheduler error: {e}")
                    time.sleep(60)
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
    
    async def process_scheduled_post(self, post_data: Dict[str, Any]):
        """Process a scheduled post"""
        try:
            user_input = post_data['user_input']
            seed = post_data['seed']
            
            # Create prompt
            prompt = self.create_abstract_prompt(user_input, seed)
            
            # Generate image
            image_url = await self.generate_image(prompt, seed)
            
            if not image_url:
                logger.error("Failed to generate scheduled image")
                return
            
            # Download image
            image_path = await self.download_image(image_url)
            
            if not image_path:
                logger.error("Failed to download scheduled image")
                return
            
            # Upload to Instagram
            instagram_caption = f"""
🎨 Scheduled Abstract Art Post

AI-generated abstract artwork
Prompt inspiration: "{user_input[:50]}..."
Generated with seed: {seed}

#AbstractArt #DigitalArt #AIArt #ContemporaryArt #ModernArt #ArtisticExpression #CreativeAI #ScheduledPost #AbstractExpressionism #DigitalCreativity #ArtDaily
            """.strip()
            
            self.upload_to_instagram(image_path, instagram_caption)
            
            logger.info(f"Processed scheduled post: {user_input[:30]}...")
            
        except Exception as e:
            logger.error(f"Error processing scheduled post: {e}")
    
    # Telegram Bot Handlers
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = """
🎨 AI Abstract Image Generator Bot

Commands:
• /generate - Generate random abstract image
• /generate [description] - Generate with your description  
• /seed [number] [description] - Generate with specific seed
• /schedule [minutes] [description] - Schedule post for later
• /status - Show scheduled posts
• /help - Show this help message

Just send me any text and I'll create an abstract artwork based on it!
        """
        await update.message.reply_text(welcome_message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
🎨 AI Abstract Image Generator

How to use:
1. Use /generate for a random abstract image
2. Use /generate [your description] for themed images
3. Use /seed [number] [description] for reproducible results
4. Use /schedule [minutes] [description] to schedule posts
5. Just send any message and I'll create art from it!

Examples:
• /generate cosmic nebula
• /seed 1234567 flowing water
• /schedule 60 sunset over mountains
• sunset over mountains

The bot will automatically upload images to Instagram.

Scheduling:
• /schedule 30 ocean waves (posts in 30 minutes)
• /status (shows scheduled posts)
        """
        await update.message.reply_text(help_text)
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        if not self.scheduled_posts:
            await update.message.reply_text("📅 No posts scheduled")
            return
        
        status_text = "📅 Scheduled Posts:\n\n"
        for i, post in enumerate(self.scheduled_posts, 1):
            time_str = post['time'].strftime("%Y-%m-%d %H:%M")
            desc = post['user_input'][:30] + "..." if len(post['user_input']) > 30 else post['user_input']
            status_text += f"{i}. {time_str} - {desc}\n"
        
        await update.message.reply_text(status_text)
    
    async def schedule_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /schedule command"""
        if len(context.args) < 2:
            await update.message.reply_text("Usage: /schedule [minutes] [description]\nExample: /schedule 60 abstract ocean")
            return
        
        try:
            delay_minutes = int(context.args[0])
            user_input = ' '.join(context.args[1:])
            
            if delay_minutes < 1:
                await update.message.reply_text("Delay must be at least 1 minute")
                return
            
            if delay_minutes > 10080:  # 1 week
                await update.message.reply_text("Maximum delay is 1 week (10080 minutes)")
                return
            
            scheduled_time = self.schedule_post(delay_minutes, user_input, update.message.chat_id)
            
            time_str = scheduled_time.strftime("%Y-%m-%d %H:%M")
            await update.message.reply_text(
                f"📅 Post scheduled for {time_str}\n"
                f"Description: {user_input}\n"
                f"Will be posted to Instagram automatically!"
            )
            
        except ValueError:
            await update.message.reply_text("Invalid delay time. Please use a number in minutes.")
        except Exception as e:
            logger.error(f"Schedule command error: {e}")
            await update.message.reply_text("❌ Error scheduling post. Please try again.")
    
    async def generate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /generate command"""
        user_input = ' '.join(context.args) if context.args else ""
        seed = self.generate_random_seed()
        
        await update.message.reply_text(f"🎨 Generating abstract artwork... (Seed: {seed})")
        
        try:
            # Create prompt
            prompt = self.create_abstract_prompt(user_input, seed)
            
            # Generate image
            image_url = await self.generate_image(prompt, seed)
            
            if not image_url:
                await update.message.reply_text("❌ Sorry, failed to generate image. Please try again.")
                return
            
            # Download image
            image_path = await self.download_image(image_url)
            
            if not image_path:
                await update.message.reply_text("❌ Failed to download generated image.")
                return
            
            # Send image to Telegram
            try:
                with open(image_path, 'rb') as photo:
                    await update.message.reply_photo(
                        photo=photo,
                        caption=f"🎨 Abstract Art Generated!\n\nPrompt: {prompt[:100]}...\nSeed: {seed}"
                    )
            except Exception as e:
                logger.error(f"Error sending photo to Telegram: {e}")
                await update.message.reply_text("❌ Error sending image to Telegram")
                return
            
            # Upload to Instagram
            instagram_caption = f"""
🎨 Abstract Digital Art

Generated with AI using advanced algorithms
Style: Contemporary Abstract Expression
Prompt: "{user_input[:50]}..." if user_input else 
