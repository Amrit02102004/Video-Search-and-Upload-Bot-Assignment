import os
import sys
import asyncio
import logging
from typing import List
from dotenv import load_dotenv
from instadownloader import download_instagram_videos
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
            logging.FileHandler('video_workflow.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def validate_inputs(tags: List[str], videos_per_tag: int) -> bool:
    """
    Validate user inputs before processing.
    
    :param tags: List of hashtags to search
    :param videos_per_tag: Number of videos to download per tag
    :return: Boolean indicating input validity
    """
    if not tags:
        print("❌ Error: At least one tag is required.")
        return False
    
    if videos_per_tag <= 0:
        print("❌ Error: Number of videos must be a positive integer.")
        return False
    
    return True

async def async_main():
    """
    Asynchronous main workflow orchestrating video download and upload process.
    Interactive CLI for user-friendly experience.
    """
    # Setup logging
    logger = setup_logging()
    
    try:
        # User Input Section - Enhanced UX
        print("🎥 Instagram Video Workflow Automation 🚀")
        print("-------------------------------------")
        
        # Collect Tags
        tags_input = input("Enter hashtags (comma-separated): ").strip()
        tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
        
        # Collect Number of Videos
        videos_per_tag = int(input("Enter number of videos per tag: "))
        
        # Input Validation
        if not validate_inputs(tags, videos_per_tag):
            sys.exit(1)
        
        # Log Workflow Start
        logger.info(f"Starting workflow with tags: {tags}, Videos per tag: {videos_per_tag}")
        
        # Stage 1: Video Download
        print("\n🔍 Downloading Videos...")
        downloaded_videos = download_instagram_videos(tags, videos_per_tag)
        
        if not downloaded_videos:
            print("❌ No videos were downloaded. Check your internet connection or API limits.")
            sys.exit(1)
        
        print(f"✅ Successfully downloaded {len(downloaded_videos)} videos.")
        
        # Stage 2: Video Upload
        print("\n📤 Starting Video Upload...")
        
        FLIC_TOKEN = os.getenv('FLIC_TOKEN')
        CATEGORY_ID = 25
        
        # Initialize Uploader
        uploader = SimpleVideoUploader(FLIC_TOKEN)
        
        # Upload each downloaded video asynchronously
        upload_tasks = []
        for video in downloaded_videos:
            video_filename = os.path.basename(video)
            print(f"\nUploading: {video_filename}")
            
            # Create upload task
            upload_task = asyncio.create_task(
                uploader.upload_single_video(
                    video_filename, 
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
        print(f"Total Videos: {len(downloaded_videos)}")
        print(f"Successful Uploads: {successful_uploads}")
        print(f"Failed Uploads: {failed_uploads}")
        
        if failed_uploads > 0:
            print("⚠️ Some videos failed to upload. Check logs for details.")
    
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