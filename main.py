import os
import sys
import asyncio
import logging
from typing import List
from dotenv import load_dotenv

# Assuming these modules exist in the same directory
from instadownloader import download_instagram_videos
from imagedownloader import download_instagram_images  # Our newly created image downloader
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
        # User Input Section - Enhanced UX
        print("🎥📸 Instagram Media Workflow Automation 🚀")
        print("---------------------------------------")
        
        # Collect Tags
        tags_input = input("Enter hashtags (comma-separated): ").strip()
        tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
        
        # Validate tags
        if not validate_inputs(tags, 1, "tags"):
            sys.exit(1)
        
        # Collect Number of Videos
        videos_per_tag = int(input("Enter number of VIDEOS per tag: "))
        
        # Validate video input
        if not validate_inputs(tags, videos_per_tag, "videos"):
            sys.exit(1)
        
        # Collect Number of Images
        images_per_tag = int(input("Enter number of IMAGES per tag: "))
        
        # Validate image input
        if not validate_inputs(tags, images_per_tag, "images"):
            sys.exit(1)
        
        # Log Workflow Start
        logger.info(f"Starting workflow with tags: {tags}")
        logger.info(f"Videos per tag: {videos_per_tag}, Images per tag: {images_per_tag}")
        
        # Stage 1: Video Download
        print("\n🎥 Downloading Videos...")
        downloaded_videos = download_instagram_videos(tags, videos_per_tag)
        
        print(f"✅ Successfully downloaded {len(downloaded_videos)} videos.")
        
        # Stage 2: Image Download
        print("\n📸 Downloading Images...")
        downloaded_images = download_instagram_images(tags, images_per_tag)
        
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
        uploader = SimpleVideoUploader(FLIC_TOKEN , CATEGORY_ID)
        
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