import os
import requests
import logging
import certifi
import ssl
from tqdm import tqdm
import socket
import urllib3

class SimpleVideoUploader:
    def __init__(self, flic_token, videos_directory='videos'):
        """
        Initialize SimpleVideoUploader with robust logging and connection handling
        
        :param flic_token: Authentication token for the API
        :param videos_directory: Directory containing video files
        """
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Disable SSL warnings
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        self.flic_token = flic_token
        self.videos_directory = videos_directory
        
        # Create videos directory if it doesn't exist
        os.makedirs(videos_directory, exist_ok=True)
        
        # Configure requests session with robust settings
        self.session = requests.Session()
        self.session.verify = certifi.where()
        
        # Configure socket and SSL timeouts
        socket.setdefaulttimeout(30)
        ssl.create_default_https_context = ssl.create_default_context

    def _upload_with_progress(self, file_path, upload_url):
        """
        Enhanced file upload with improved error handling and progress tracking
        
        :param file_path: Path to the file to upload
        :param upload_url: Pre-signed S3 upload URL
        :return: Success status
        """
        try:
            # Get file size for progress bar
            file_size = os.path.getsize(file_path)
            
            # Open file and create progress bar
            with open(file_path, 'rb') as f, tqdm(
                total=file_size, 
                unit='B', 
                unit_scale=True, 
                desc=os.path.basename(file_path),
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]'
            ) as pbar:
                # Custom iterator to update progress bar
                def iter_file():
                    # Increased chunk size to 30MB as requested
                    chunk_size = 1024 * 1024 * 30 
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        pbar.update(len(chunk))
                        yield chunk
                
                # Configure additional request parameters
                upload_params = {
                    'data': iter_file(),
                    'headers': {
                        'Content-Length': str(file_size),
                        'Content-Type': 'video/mp4'
                    },
                    'verify': certifi.where(),
                    'stream': True,
                    'timeout': (30, 60)  # Extended timeouts
                }
                
                # Retry mechanism for upload
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = requests.put(upload_url, **upload_params)
                        response.raise_for_status()
                        return True
                    except requests.exceptions.RequestException as e:
                        self.logger.warning(f"Upload attempt {attempt + 1} failed: {e}")
                        if attempt == max_retries - 1:
                            raise
            
        except Exception as e:
            self.logger.error(f"Comprehensive upload error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def upload_single_video(self, file_name, category_id=25, max_retries=3):
        """
        Robust single video upload with comprehensive error handling
        
        :param file_name: Name of the video file to upload
        :param category_id: Category ID for the post
        :param max_retries: Number of retry attempts
        :return: Success status
        """
        file_path = os.path.join(self.videos_directory, file_name)
        
        try:
            # Validate file existence
            if not os.path.exists(file_path):
                self.logger.error(f"Video file not found: {file_path}")
                return False
            
            # Retry mechanism for API calls
            for attempt in range(max_retries):
                try:
                    # Step 1: Get Upload URL
                    upload_url_response = self.session.get(
                        'https://api.socialverseapp.com/posts/generate-upload-url',
                        headers={
                            'Flic-Token': self.flic_token,
                            'Content-Type': 'application/json'
                        },
                        json={'file_size': os.path.getsize(file_path)},
                        timeout=(30, 60)
                    )
                    
                    # Validate upload URL response
                    upload_url_data = upload_url_response.json()
                    if upload_url_data.get('status') != 'success':
                        self.logger.error(f"Upload URL request failed (Attempt {attempt + 1})")
                        if attempt == max_retries - 1:
                            return False
                        continue
                    
                    upload_url = upload_url_data.get('url')
                    file_hash = upload_url_data.get('hash')
                    
                    # Step 2: Upload Video
                    if not self._upload_with_progress(file_path, upload_url):
                        raise ValueError("Video upload failed")
                    
                    # Step 3: Create Post
                    post_response = self.session.post(
                        'https://api.socialverseapp.com/posts',
                        headers={
                            'Flic-Token': self.flic_token,
                            'Content-Type': 'application/json'
                        },
                        json={
                            'title': f'{os.path.splitext(file_name)[0]}_upload',
                            'hash': file_hash,
                            'is_available_in_public_feed': False,
                            'category_id': category_id
                        },
                        timeout=(30, 60)
                    )
                    
                    post_response.raise_for_status()
                    self.logger.info(f"Successfully uploaded {file_name}")
                    return True
                
                except Exception as attempt_error:
                    self.logger.warning(f"Upload attempt {attempt + 1} failed: {attempt_error}")
                    if attempt == max_retries - 1:
                        return False
        
        except Exception as e:
            self.logger.error(f"Critical error uploading {file_name}: {e}")
            import traceback
            traceback.print_exc()
            return False