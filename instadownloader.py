import os
import requests
import logging
import time
import random
from dotenv import load_dotenv
load_dotenv()
class InstagramVideoDownloader:
    def __init__(self, tags, max_videos=3):
        """
        Instagram Video Downloader using RapidAPI with enhanced logging
        
        :param tags: List of hashtags to search
        :param max_videos: Maximum number of videos to download per tag
        """
        # Configure logging
        logging.basicConfig(
            level=logging.INFO, 
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('instagram_downloader.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

        self.tags = tags
        self.max_videos = max_videos
        self.videos_directory = 'videos'
        
        # Create videos directory
        os.makedirs(self.videos_directory, exist_ok=True)
        
        # RapidAPI configuration
        self.rapid_api_key = os.getenv('RAPID_API_KEY')
        self.rapid_api_host = os.getenv('RAPID_API_HOST')
        
        # Headers for RapidAPI request
        self.headers = {
            'x-rapidapi-host': self.rapid_api_host,
            'x-rapidapi-key': self.rapid_api_key
        }
        
        # Log initialization details
        self.logger.info(f"Initialized downloader with tags: {tags}")
        self.logger.info(f"Max videos per tag: {max_videos}")
    
    def download_videos_from_hashtag(self):
        """
        Download videos using RapidAPI hashtag endpoint
        
        :return: List of downloaded video paths
        """
        downloaded_videos = []
        
        for tag in self.tags:
            tag_videos_count = 0
            try:
                # Log start of hashtag processing
                self.logger.info(f"Processing hashtag: {tag}")

                # Construct URL for hashtag search
                url = f'https://{self.rapid_api_host}/v1/hashtag'
                
                # Query parameters
                querystring = {"hashtag": tag}
                
                # Log API request details
                self.logger.info(f"Sending request to URL: {url}")
                self.logger.info(f"Query parameters: {querystring}")
                
                # Make API request
                response = requests.get(url, headers=self.headers, params=querystring)
                
                # Log response details
                self.logger.info(f"Response status code: {response.status_code}")
                data = response.json()
                
                items = data.get('data', {}).get('items', [])
                self.logger.info(f"Found {len(items)} items for tag: {tag}")
                for index, item in enumerate(items[:self.max_videos], 1):
                    # Extract video URL - the exact key might vary based on API response
                    video_url = item.get('video_url')
                    self.logger.info(f"Found video URL {index}: {video_url}")
                    if video_url:
                        video_response = requests.get(video_url)
                        if video_response.status_code == 200:
                            # Generate unique filename
                            filename = os.path.join(
                                self.videos_directory, 
                                f"{tag}_{index}_video.mp4"
                            )
                            
                            # Save video
                            with open(filename, 'wb') as f:
                                f.write(video_response.content)
                            
                            downloaded_videos.append(filename)
                            self.logger.info(f"Successfully downloaded video: {filename}")
                            tag_videos_count += 1
                    
                    # Break if max videos per tag is reached
                    if tag_videos_count >= self.max_videos:
                        break
                
            except Exception as e:
                self.logger.error(f"Unexpected error processing tag {tag}: {e}")
        
        self.logger.info(f"Total videos downloaded: {len(downloaded_videos)}")
        return downloaded_videos

def download_instagram_videos(tags, max_videos=3):
    """
    Convenience function to download Instagram videos
    
    :param tags: List of hashtags to search
    :param max_videos: Maximum number of videos to download per tag
    :return: List of downloaded video paths
    """
    downloader = InstagramVideoDownloader(tags, max_videos)
    return downloader.download_videos_from_hashtag()