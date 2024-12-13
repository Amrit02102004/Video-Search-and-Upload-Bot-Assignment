import os
import logging
import json
import asyncio
import aiofiles
import aiohttp
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleVideoUploader:
    def __init__(self, flic_token, category_id , chunk_size=5 * 1024 * 1024):  # 5MB chunks
        self.flic_token = flic_token
        self.chunk_size = chunk_size
        self.base_url = 'https://api.socialverseapp.com'
        self.category_id = category_id

    async def get_upload_url(self, file_size):
        """Generate pre-signed upload URL"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f'{self.base_url}/posts/generate-upload-url', 
                headers={
                    'Flic-Token': self.flic_token,
                    'Content-Type': 'application/json'
                },
                json={'file_size': file_size}
            ) as response:
                data = await response.json()
                logger.info(f"Upload URL Response: {json.dumps(data, indent=2)}")
                
                if data.get('status') != 'success':
                    raise ValueError("Failed to get upload URL")
                
                return data.get('url'), data.get('hash')

    async def chunked_upload(self, file_path, upload_url):
        """Upload file in chunks with progress tracking"""
        file_size = os.path.getsize(file_path)
        
        # Use tqdm for progress bar
        with tqdm(total=file_size, unit='B', unit_scale=True, desc=os.path.basename(file_path)) as pbar:
            async with aiofiles.open(file_path, 'rb') as f:
                async with aiohttp.ClientSession() as session:
                    async with session.put(upload_url, headers={'Content-Type': 'video/mp4'}) as response:
                        while True:
                            chunk = await f.read(self.chunk_size)
                            if not chunk:
                                break
                            
                            try:
                                async with session.put(upload_url, data=chunk) as chunk_response:
                                    if chunk_response.status not in [200, 204]:
                                        logger.error(f"Chunk upload failed: {chunk_response.status}")
                                        return False
                                
                                pbar.update(len(chunk))
                            except Exception as e:
                                logger.error(f"Chunk upload error: {e}")
                                return False
                        
                        return True

    async def create_post(self, file_path, file_hash, category_id=25):
        """Create post after successful upload"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{self.base_url}/posts', 
                headers={
                    'Flic-Token': self.flic_token,
                    'Content-Type': 'application/json'
                },
                json={
                    'title': f'{os.path.splitext(os.path.basename(file_path))[0]}_upload',
                    'hash': file_hash,
                    'is_available_in_public_feed': False,
                    'category_id': category_id
                }
            ) as response:
                response_data = await response.json()
                logger.info(f"Post Response: {json.dumps(response_data, indent=2)}")
                
                return response.status in [200, 201]

    async def upload_single_video(self, file_path, category_id=25):
        """Main upload method with comprehensive error handling"""
        try:
            # Ensure full path if only filename is provided
            if not os.path.isabs(file_path):
                file_path = os.path.join('videos', file_path)
            
            file_size = os.path.getsize(file_path)
            
            # Get upload URL
            upload_url, file_hash = await self.get_upload_url(file_size)
            
            # Chunked upload
            upload_success = await self.chunked_upload(file_path, upload_url)
            
            if not upload_success:
                logger.error("Video upload failed")
                return False
            
            # Create post
            post_success = await self.create_post(file_path, file_hash, category_id)
            
            if not post_success:
                logger.error("Post creation failed")
                return False
            
            logger.info(f"Successfully uploaded {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"Upload error: {e}")
            import traceback
            traceback.print_exc()
            return False