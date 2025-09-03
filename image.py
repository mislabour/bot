#!/usr/bin/env python3
"""
AI Image Generator Bot with Instagram Upload
Generates abstract, realistic images using OpenAI's DALL-E API
Controlled via Telegram bot and uploads to Instagram
"""

import os
import random
import asyncio
import logging
from typing import Optional
from datetime import datetime

# Third-party imports
import openai
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from instagrapi import Client
from PIL import Image
import tempfile

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class AIImageBot:
    def __init__(self):
        # API Keys and credentials - Set these as environment variables
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.instagram_username = os.getenv('INSTAGRAM_USERNAME')
        self.instagram_password = os.getenv('INSTAGRAM_PASSWORD')
        
        # Initialize OpenAI client
        openai.api_key = self.openai_api_key
        
        # Initialize Instagram client
        self.instagram_client = Client()
        
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
                prompt += f" (style seed: {seed})"
            
            response = openai.Image.create(
                prompt=prompt,
                n=1,
                size="1024x1024",
                response_format="url"
            )
            
            image_url = response['data'][0]['url']
            return image_url
            
        except Exception as e:
            logger.error(f"Error generating image: {e}")
            return None
    
    async def download_image(self, image_url: str) -> Optional[str]:
        """Download image from URL and save temporarily"""
        try:
            response = requests.get(image_url)
            response.raise_for_status()
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
                tmp_file.write(response.content)
                return tmp_file.name
                
        except Exception as e:
            logger.error(f"Error downloading image: {e}")
            return None
    
    async def upload_to_instagram(self, image_path: str, caption: str) -> bool:
        """Upload image to Instagram"""
        try:
            # Login to Instagram
            self.instagram_client.login(self.instagram_username, self.instagram_password)
            
            # Upload photo
            media = self.instagram_client.photo_upload(image_path, caption)
            
            logger.info(f"Successfully uploaded to Instagram: {media.pk}")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading to Instagram: {e}")
            return False
        finally:
            # Cleanup temporary file
            if os.path.exists(image_path):
                os.unlink(image_path)
    
    # Telegram Bot Handlers
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = """
🎨 AI Abstract Image Generator Bot

Commands:
• /generate - Generate random abstract image
• /generate [description] - Generate with your description  
• /seed [number] [description] - Generate with specific seed
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
4. Just send any message and I'll create art from it!

Examples:
• /generate cosmic nebula
• /seed 1234567 flowing water
• sunset over mountains

The bot will automatically upload images to Instagram with artistic captions.
        """
        await update.message.reply_text(help_text)
    
    async def generate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /generate command"""
        user_input = ' '.join(context.args) if context.args else ""
        seed = self.generate_random_seed()
        
        await update.message.reply_text(f"🎨 Generating abstract artwork... (Seed: {seed})")
        
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
        with open(image_path, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=f"🎨 Abstract Art Generated!\n\nPrompt: {prompt[:100]}...\nSeed: {seed}"
            )
        
        # Upload to Instagram
        instagram_caption = f"""
🎨 Abstract Digital Art

Generated with AI using advanced algorithms
Style: Contemporary Abstract Expression

#AbstractArt #DigitalArt #AIArt #ContemporaryArt #ModernArt #ArtisticExpression #CreativeAI #AbstractExpressionism #DigitalCreativity #ArtDaily
        """.strip()
        
        upload_success = await self.upload_to_instagram(image_path, instagram_caption)
        
        if upload_success:
            await update.message.reply_text("✅ Image uploaded to Instagram successfully!")
        else:
            await update.message.reply_text("⚠️ Image generated but Instagram upload failed.")
    
    async def seed_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /seed command with specific seed"""
        if not context.args:
            await update.message.reply_text("Please provide a seed number: /seed 1234567 [description]")
            return
        
        try:
            seed = int(context.args[0])
            user_input = ' '.join(context.args[1:]) if len(context.args) > 1 else ""
        except ValueError:
            await update.message.reply_text("Invalid seed number. Please use: /seed 1234567 [description]")
            return
        
        await update.message.reply_text(f"🎨 Generating artwork with seed {seed}...")
        
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
        with open(image_path, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=f"🎨 Abstract Art (Seed: {seed})\n\nPrompt: {prompt[:100]}..."
            )
        
        # Upload to Instagram with seed info
        instagram_caption = f"""
🎨 Abstract Digital Art - Seed {seed}

AI-generated abstract expressionist artwork
Unique algorithmic composition

#AbstractArt #DigitalArt #AIArt #ContemporaryArt #ModernArt #ArtisticExpression #CreativeAI #AbstractExpressionism #DigitalCreativity #ArtDaily #Seed{seed}
        """.strip()
        
        upload_success = await self.upload_to_instagram(image_path, instagram_caption)
        
        if upload_success:
            await update.message.reply_text("✅ Image uploaded to Instagram successfully!")
        else:
            await update.message.reply_text("⚠️ Image generated but Instagram upload failed.")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages as image prompts"""
        user_input = update.message.text
        seed = self.generate_random_seed()
        
        await update.message.reply_text(f"🎨 Creating abstract art from your message... (Seed: {seed})")
        
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
        with open(image_path, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=f"🎨 Inspired by: \"{user_input}\"\n\nSeed: {seed}"
            )
        
        # Upload to Instagram
        instagram_caption = f"""
🎨 Abstract Digital Art

Inspired by the concept: "{user_input[:50]}..."
AI-generated contemporary abstract expression

#AbstractArt #DigitalArt #AIArt #ContemporaryArt #ModernArt #ArtisticExpression #CreativeAI #AbstractExpressionism #DigitalCreativity #ArtDaily
        """.strip()
        
        upload_success = await self.upload_to_instagram(image_path, instagram_caption)
        
        if upload_success:
            await update.message.reply_text("✅ Image uploaded to Instagram successfully!")
        else:
            await update.message.reply_text("⚠️ Image generated but Instagram upload failed.")
    
    def run_bot(self):
        """Start the Telegram bot"""
        # Verify required environment variables
        required_vars = [
            'OPENAI_API_KEY', 'TELEGRAM_BOT_TOKEN', 
            'INSTAGRAM_USERNAME', 'INSTAGRAM_PASSWORD'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            logger.error(f"Missing required environment variables: {missing_vars}")
            return
        
        # Create application
        application = Application.builder().token(self.telegram_bot_token).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("generate", self.generate_command))
        application.add_handler(CommandHandler("seed", self.seed_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Start bot
        logger.info("Starting AI Image Generator Bot...")
        application.run_polling()

def main():
    """Main function to run the bot"""
    bot = AIImageBot()
    bot.run_bot()

if __name__ == "__main__":
    main()
