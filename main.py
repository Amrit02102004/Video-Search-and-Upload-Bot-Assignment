import os
import sys
import asyncio
import logging
from typing import List
from dotenv import load_dotenv

# Gemini API imports
import google.generativeai as genai

# Assuming these modules exist in the same directory
from instadownloader import download_instagram_videos
from imagedownloader import download_instagram_images
from videouploader import SimpleVideoUploader

# Load environment variables
load_dotenv()

def setup_logging():
    """
    Configure logging for the main application.
    Provides clear, informative logging to track the entire process.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler('media_workflow.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def generate_motivational_hashtags(prompt: str, model: genai.GenerativeModel) -> List[str]:
    """
    Generate motivational and positive hashtags using Gemini API
    
    :param prompt: User's original prompt
    :param model: Gemini AI model
    :return: List of generated motivational hashtags
    """
    try:
        hashtag_prompt = f"""Transform the following input into ONLY motivational, positive, and inspiring Instagram hashtags. 
        Avoid negative or demotivational tags. Focus on empowerment, growth, and positivity.
        
        Input: "{prompt}"
        
        Guidelines:
        - Create hashtags that inspire and uplift
        - Mix single-word and combined hashtags
        - Emphasize personal growth, motivation, and success
        - Avoid tags that highlight negative emotions
        
        Output Format:
        - 3-4 single-word motivational hashtags
        - 2-3 combined motivational hashtags
        
        Examples of good hashtags:
        #motivation #success #growth #mindset
        #personalgrowth #successmindset #positivevibes #believeinyourself
        """
        
        response = model.generate_content(hashtag_prompt)
        
        # Split the response and clean up hashtags
        all_hashtags = []
        for line in response.text.split('\n'):
            line_hashtags = [tag.strip() for tag in line.split() if tag.strip().startswith('#')]
            all_hashtags.extend(line_hashtags)
        
        # Remove duplicates and limit to unique hashtags
        unique_hashtags = list(dict.fromkeys(all_hashtags))[:6]
        
        # Fallback to default motivational hashtags if generation fails
        if not unique_hashtags:
            unique_hashtags = [
                '#motivation', '#success', '#mindset', 
                '#personalgrowth', '#positivevibes', 
                '#believeinyourself'
            ]
        
        return unique_hashtags
    except Exception as e:
        print(f"❌ Error generating hashtags: {e}")
        # Fallback motivational hashtags
        return [
            '#motivation', '#success', '#mindset', 
            '#personalgrowth', '#positivevibes', 
            '#believeinyourself'
        ]

def validate_inputs(tags: List[str], media_count: int, media_type: str) -> bool:
    """
    Validate user inputs before processing.
    
    :param tags: List of hashtags to search
    :param media_count: Number of media to download per tag
    :param media_type: Type of media (videos or images)
    :return: Boolean indicating input validity
    """
    if not tags:
        print(f"❌ Error: At least one tag is required for {media_type}.")
        return False
    
    if media_count <= 0:
        print(f"❌ Error: Number of {media_type} must be a positive integer.")
        return False
    
    return True

def get_user_confirmation(prompt: str) -> bool:
    """
    Get user confirmation with a yes/no prompt
    
    :param prompt: Confirmation message to display
    :return: Boolean indicating user's choice
    """
    while True:
        response = input(f"{prompt} (yes/no): ").strip().lower()
        if response in ['yes', 'y']:
            return True
        elif response in ['no', 'n']:
            return False
        else:
            print("Please respond with 'yes' or 'no'.")

async def async_main():
    """
    Asynchronous main workflow orchestrating video and image download and upload process.
    Interactive CLI for user-friendly experience.
    """
    # Setup logging
    logger = setup_logging()
    
    try:
        # Setup Gemini API
        GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
        if not GEMINI_API_KEY:
            print("❌ Error: GEMINI_API_KEY not found in .env file")
            sys.exit(1)
        
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-pro')
        
        # User Input Section - Enhanced UX
        print("🎥📸 Motivational Media Workflow Automation 🚀")
        print("---------------------------------------")
        
        # Collect User Prompt
        user_prompt = input("Enter your motivation/goal prompt: ").strip()
        
        # Generate Motivational Hashtags
        tags = generate_motivational_hashtags(user_prompt, gemini_model)
        
        # Validate tags
        if not validate_inputs(tags, 1, "tags"):
            sys.exit(1)
        
        # Collect Number of Videos and Images per Tag
        videos_per_tag = 2  # Automatic 2 videos per tag
        images_per_tag = 2  # Automatic 2 images per tag
        
        # Validate input
        if not validate_inputs(tags, videos_per_tag, "videos"):
            sys.exit(1)
        
        # Log Workflow Start
        logger.info(f"Starting workflow with prompt: {user_prompt}")
        logger.info(f"Generated Motivational Hashtags: {tags}")
        logger.info(f"Videos per tag: {videos_per_tag}, Images per tag: {images_per_tag}")
        
        # Stage 1: Video Download
        print("\n🎥 Downloading Motivational Videos...")
        downloaded_videos = []
        for tag in tags:
            videos = download_instagram_videos([tag], videos_per_tag)
            downloaded_videos.extend(videos)
            
            # Break if we've reached our desired number of videos
            if len(downloaded_videos) >= len(tags) * videos_per_tag:
                break
        
        print(f"✅ Successfully downloaded {len(downloaded_videos)} videos.")
        
        # Stage 2: Image Download
        print("\n📸 Downloading Motivational Images...")
        downloaded_images = []
        for tag in tags:
            images = download_instagram_images([tag], images_per_tag)
            downloaded_images.extend(images)
            
            # Break if we've reached our desired number of images
            if len(downloaded_images) >= len(tags) * images_per_tag:
                break
        
        print(f"✅ Successfully downloaded {len(downloaded_images)} images.")
        
        # Combine downloaded media
        downloaded_media = downloaded_videos + downloaded_images
        
        # Check if any media was downloaded
        if not downloaded_media:
            print("❌ No media were downloaded. Check your internet connection or API limits.")
            sys.exit(1)
        
        # Confirmation before upload
        print("\n📤 Media Download Complete")
        print("Media Files:")
        for media in downloaded_media:
            print(f"  - {os.path.basename(media)}")
        
        # Ask for upload confirmation
        proceed_with_upload = get_user_confirmation("\n🤔 Do you want to proceed with uploading these media files?")
        
        if not proceed_with_upload:
            print("❌ Upload cancelled by user. Media files are saved locally.")
            sys.exit(0)
        
        # Stage 3: Video Upload
        print("\n📤 Starting Media Upload...")
        
        FLIC_TOKEN = os.getenv('FLIC_TOKEN')
        CATEGORY_ID = 25
        
        # Initialize Uploader
        uploader = SimpleVideoUploader(FLIC_TOKEN, CATEGORY_ID)
        
        # Upload each downloaded media file asynchronously
        upload_tasks = []
        for media in downloaded_media:
            media_filename = os.path.basename(media)
            print(f"\nUploading: {media_filename}")
            
            # Create upload task
            upload_task = asyncio.create_task(
                uploader.upload_single_video(
                    media_filename, 
                    category_id=CATEGORY_ID
                )
            )
            upload_tasks.append(upload_task)
        
        # Wait for all uploads to complete
        upload_results = await asyncio.gather(*upload_tasks)
        
        # Count successful and failed uploads
        successful_uploads = upload_results.count(True)
        failed_uploads = upload_results.count(False)
        
        # Final Summary
        print("\n📊 Upload Summary:")
        print(f"Total Media: {len(downloaded_media)}")
        print(f"Successful Uploads: {successful_uploads}")
        print(f"Failed Uploads: {failed_uploads}")
        
        if failed_uploads > 0:
            print("⚠️ Some media files failed to upload. Check logs for details.")
    
    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user.")
    
    except Exception as e:
        logger.error(f"Unexpected error in main workflow: {e}")
        print(f"❌ An unexpected error occurred: {e}")
        sys.exit(1)

def main():
    """
    Synchronous wrapper for async main function
    """
    asyncio.run(async_main())

if __name__ == "__main__":
    main()