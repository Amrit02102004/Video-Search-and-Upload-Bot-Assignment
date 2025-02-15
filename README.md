# 🎥 Instagram Video Downloader and Uploader

## Demo Video : https://drive.google.com/file/d/1ix_XlXGloME2O8rFMQiv1-HUrOE-JNkX/view?usp=drive_link

## 📝 Project Overview
This project is a robust, end-to-end solution for downloading Instagram videos by hashtag and uploading them to a social media platform. Perfect for content aggregation and social media management.

## 🚀 Features
- Interactive CLI for video download
- Hashtag-based video search
- Configurable download limits
- Progress tracking
- Comprehensive logging
- Retry mechanisms for uploads
- Error handling

## 🔧 Prerequisites
- Python 3.8+
- RapidAPI Account
- Flic Authentication Token
- Internet Connection

## 📦 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/instagram-video-workflow.git
cd instagram-video-workflow
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```
### 4. Set up .env file
```bash
# In your .env.example file

FLIC_TOKEN = your_flic_token
RAPID_API_KEY = your_rapid_api_key
RAPID_API_HOST = your_rapid_api_host
```
After Setting this up. 
Rename the .env.example to .env

## 💻 Usage
```bash
python main.py
```
Follow the interactive prompts:
- Enter hashtags (comma-separated)
- Specify videos per tag

## 📊 Workflow
1. Search Instagram videos by hashtag
2. Download specified number of videos
3. Upload videos to platform
4. Generate detailed logs

