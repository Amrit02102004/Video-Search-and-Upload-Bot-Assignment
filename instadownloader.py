import os
import csv
import requests
import logging
import time
import random
from typing import Set, Dict, List, Tuple

from dotenv import load_dotenv
load_dotenv()

class InstagramVideoDownloader:
    def __init__(self, tags, max_videos=3):
        """
        Optimized Instagram Video Downloader with in-memory download history and pagination
        
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
        self.history_file = 'download_history.csv'
        
        # In-memory set to track downloaded PKs
        self.downloaded_pks: Set[str] = set()
        
        # Create directories
        os.makedirs(self.videos_directory, exist_ok=True)
        
        # Load existing download history into memory
        self._load_download_history()
        
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
        self.logger.info(f"Loaded {len(self.downloaded_pks)} existing video PKs")
    
    def _load_download_history(self):
        """
        Load download history into memory for fast lookup
        """
        try:
            # Create file if not exists
            if not os.path.exists(self.history_file):
                with open(self.history_file, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow([
                        'tag', 
                        'pk', 
                        'timestamp', 
                        'video_url', 
                        'filename'
                    ])
            
            # Read existing history
            with open(self.history_file, 'r') as csvfile:
                reader = csv.reader(csvfile)
                next(reader) 
                
                self.downloaded_pks = {
                    str(row[1]) for row in reader 
                    if len(row) > 1
                }
        
        except Exception as e:
            self.logger.error(f"Error loading download history: {e}")
            self.downloaded_pks = set()
    
    def _is_video_downloaded(self, pk):
        """
        Check if a video with given pk has been previously downloaded
        Using in-memory set for O(1) lookup
        
        :param pk: Unique identifier for the video
        :return: Boolean indicating if video was previously downloaded
        """
        return str(pk) in self.downloaded_pks
    
    def _record_download(self, tag, pk, video_url, filename):
        """
        Record downloaded video in history CSV and in-memory set
        
        :param tag: Hashtag used for download
        :param pk: Unique video identifier
        :param video_url: URL of the downloaded video
        :param filename: Local filename of the downloaded video
        """
        try:
            # Add to in-memory set
            self.downloaded_pks.add(str(pk))
            
            # Append to CSV
            with open(self.history_file, 'a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([
                    tag, 
                    pk, 
                    time.time(), 
                    video_url, 
                    filename
                ])
        except Exception as e:
            self.logger.error(f"Error recording download history: {e}")
    
    def download_videos_from_hashtag(self, pagination_token=None):
        """
        Download videos using RapidAPI hashtag endpoint with optimized history tracking and pagination
        
        :param pagination_token: Optional pagination token for the next set of videos
        :return: List of downloaded video paths, pagination token for the next request
        """
        downloaded_videos = []
        
        for tag in self.tags:
            tag_video_count = 0
            try:
                # Log start of hashtag processing
                self.logger.info(f"Processing hashtag: {tag}")

                # Construct URL for hashtag search
                url = f'https://{self.rapid_api_host}/v1/hashtag'
                
                # Query parameters
                querystring = {"hashtag": tag}
                if pagination_token:
                    querystring['pagination_token'] = pagination_token
                
                # Log API request details
                self.logger.info(f"Sending request to URL: {url}")
                self.logger.info(f"Query parameters: {querystring}")
                
                # Make API request with timeout
                response = requests.get(
                    url, 
                    headers=self.headers, 
                    params=querystring,
                    timeout=10
                )
                
                # Log response details
                self.logger.info(f"Response status code: {response.status_code}")
                data = response.json()
                
                items = data.get('data', {}).get('items', [])
                next_pagination_token = data.get('pagination_token')
                
                # Shuffle items to add randomness to selection
                random.shuffle(items)
                
                for index, item in enumerate(items, 1):
                    # Check if item is a video
                    if item.get('is_video', False):
                        pk = item.get('pk')
                        video_url = item.get('video_url')
                        
                        # Skip if video already downloaded
                        if self._is_video_downloaded(pk):
                            self.logger.info(f"Skipping already downloaded video with pk: {pk}")
                            continue
                        
                        if video_url:
                            try:
                                # Add small random delay to avoid potential rate limiting
                                time.sleep(random.uniform(0.5, 1.5))
                                
                                video_response = requests.get(
                                    video_url, 
                                    timeout=15  # Timeout for video download
                                )
                                
                                if video_response.status_code == 200:
                                    # Generate unique filename
                                    filename = os.path.join(
                                        self.videos_directory, 
                                        f"{tag}_{pk}_video.mp4"
                                    )
                                    
                                    # Save video
                                    with open(filename, 'wb') as f:
                                        f.write(video_response.content)
                                    
                                    # Record download in history
                                    self._record_download(tag, pk, video_url, filename)
                                    
                                    downloaded_videos.append(filename)
                                    self.logger.info(f"Successfully downloaded video: {filename}")
                                    tag_video_count += 1
                            
                            except requests.exceptions.RequestException as e:
                                self.logger.warning(f"Failed to download video: {e}")
                    
                    # Break if max videos per tag is reached
                    if tag_video_count >= self.max_videos:
                        break
                
                # Return the list of downloaded videos and the next pagination token
                return downloaded_videos, next_pagination_token
            
            except Exception as e:
                self.logger.error(f"Unexpected error processing tag {tag}: {e}")
        
        self.logger.info(f"Total videos downloaded: {len(downloaded_videos)}")
        return downloaded_videos, None

def download_instagram_videos(tags, max_videos=3):
    """
    Convenience function to download Instagram videos with pagination
    
    :param tags: List of hashtags to search
    :param max_videos: Maximum number of videos to download per tag
    :return: List of downloaded video paths
    """
    downloader = InstagramVideoDownloader(tags, max_videos)
    downloaded_videos = []
    pagination_token = None
    
    while len(downloaded_videos) < max_videos * len(tags):
        new_videos, pagination_token = downloader.download_videos_from_hashtag(pagination_token)
        downloaded_videos.extend(new_videos)
        
        if not pagination_token:
            break
    
    return downloaded_videos
