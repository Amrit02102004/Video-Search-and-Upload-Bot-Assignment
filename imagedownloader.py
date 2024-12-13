import os
import csv
import requests
import logging
import time
import random
from typing import Set, Dict

from dotenv import load_dotenv
load_dotenv()

class InstagramImageDownloader:
    def __init__(self, tags, max_images=3):
        """
        Optimized Instagram Image Downloader with in-memory download history
        
        :param tags: List of hashtags to search
        :param max_images: Maximum number of images to download per tag
        """
        # Configure logging
        logging.basicConfig(
            level=logging.INFO, 
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('instagram_image_downloader.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

        self.tags = tags
        self.max_images = max_images
        self.images_directory = 'images'
        self.history_file = 'download_history.csv'
        
        # In-memory set to track downloaded PKs
        self.downloaded_pks: Set[str] = set()
        
        # Create directories
        os.makedirs(self.images_directory, exist_ok=True)
        
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
        self.logger.info(f"Max images per tag: {max_images}")
        self.logger.info(f"Loaded {len(self.downloaded_pks)} existing image PKs")
    
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
                        'image_url', 
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
    
    def _is_image_downloaded(self, pk):
        """
        Check if an image with given pk has been previously downloaded
        Using in-memory set for O(1) lookup
        
        :param pk: Unique identifier for the image
        :return: Boolean indicating if image was previously downloaded
        """
        return str(pk) in self.downloaded_pks
    
    def _record_download(self, tag, pk, image_url, filename):
        """
        Record downloaded image in history CSV and in-memory set
        
        :param tag: Hashtag used for download
        :param pk: Unique image identifier
        :param image_url: URL of the downloaded image
        :param filename: Local filename of the downloaded image
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
                    image_url, 
                    filename
                ])
        except Exception as e:
            self.logger.error(f"Error recording download history: {e}")
    
    def download_images_from_hashtag(self):
        """
        Download images using RapidAPI hashtag endpoint with optimized history tracking
        
        :return: List of downloaded image paths
        """
        downloaded_images = []
        
        for tag in self.tags:
            tag_image_count = 0
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
                
                # Shuffle items to add randomness to selection
                random.shuffle(items)
                
                for index, item in enumerate(items, 1):
                    # Check if item is an image
                    if not item.get('is_video', True):
                        pk = item.get('pk')
                        
                        # Skip if image already downloaded
                        if self._is_image_downloaded(pk):
                            self.logger.info(f"Skipping already downloaded image with pk: {pk}")
                            continue
                        
                        # Get the first image URL from image_versions
                        image_versions = item.get('image_versions', {}).get('items', [])
                        if image_versions:
                            image_url = image_versions[0].get('url')
                            
                            if image_url:
                                try:
                                    # Add small random delay to avoid potential rate limiting
                                    time.sleep(random.uniform(0.5, 1.5))
                                    
                                    image_response = requests.get(
                                        image_url, 
                                        timeout=15  # Timeout for image download
                                    )
                                    
                                    if image_response.status_code == 200:
                                        # Generate unique filename
                                        filename = os.path.join(
                                            self.images_directory, 
                                            f"{tag}_{pk}_image.jpg"
                                        )
                                        
                                        # Save image
                                        with open(filename, 'wb') as f:
                                            f.write(image_response.content)
                                        
                                        # Record download in history
                                        self._record_download(tag, pk, image_url, filename)
                                        
                                        downloaded_images.append(filename)
                                        self.logger.info(f"Successfully downloaded image: {filename}")
                                        tag_image_count += 1
                                
                                except requests.exceptions.RequestException as e:
                                    self.logger.warning(f"Failed to download image: {e}")
                    
                    # Break if max images per tag is reached
                    if tag_image_count >= self.max_images:
                        break
                
            except Exception as e:
                self.logger.error(f"Unexpected error processing tag {tag}: {e}")
        
        self.logger.info(f"Total images downloaded: {len(downloaded_images)}")
        return downloaded_images

def download_instagram_images(tags, max_images=3):
    """
    Convenience function to download Instagram images
    
    :param tags: List of hashtags to search
    :param max_images: Maximum number of images to download per tag
    :return: List of downloaded image paths
    """
    downloader = InstagramImageDownloader(tags, max_images)
    return downloader.download_images_from_hashtag()
