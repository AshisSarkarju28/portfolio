import os
import sys
import logging
from imagekitio import ImageKit

logger = logging.getLogger("ImageKitManager")

class IMAGEKIT_VIDEO_MANAGER:
    def __init__(self):
        self.private_key = os.getenv("IMAGEKIT_PRIVATE_KEY", "")
        
        if not self.private_key:
            logger.warning("Set IMAGEKIT_PRIVATE_KEY to enable ImageKit video management.")
            
        # The modern ImageKit SDK only requires the private_key on initialization
        self.ik = ImageKit(private_key=self.private_key)

    def upload_video(self, file_bytes: bytes, file_name: str, title: str = None) -> dict:
        """
        Uploads video bytes to ImageKit using the new .files namespace.
        """
        try:
            logger.info(f"Starting video upload to ImageKit for file: {file_name}")
            # .read() must be explicitly called to pass content to the modern SDK safely
            response = self.ik.files.upload(
                file=file_bytes,
                file_name=file_name,
                use_unique_file_name=True,
                tags=[f"title:{title}"] if title else []
            )
        
            logger.info(f"Successfully uploaded: {response.url} (File ID: {response.file_id})")
            return {
                "fileId": response.file_id,
                "url": response.url
            }
            
        except Exception as e:
            logger.error(f"Error uploading video to ImageKit: {e}", exc_info=True)
            return {}

    def delete_video(self, file_id: str) -> dict:
        """
        Deletes a video from ImageKit using its unique fileId string.
        """
        try:
            logger.info(f"Attempting to delete video with File ID: {file_id}")
            self.ik.files.delete(file_id)
            logger.info(f"File {file_id} deleted successfully from ImageKit.")
            return {"result": "ok"}
        except Exception as e:
            logger.error(f"Error deleting video from ImageKit: {e}", exc_info=True)
            return {"result": "error", "message": str(e)}

    def fetch_all_videos(self) -> list:
        """
        Fetches metadata for all files containing video mime-types.
        """
        videos = []
        try:
            logger.info("Fetching all video files from ImageKit...")
            # In imagekitio v5, file listing is under assets.list()
            response = self.ik.assets.list(file_type="non-image")
            
            # The response is usually a list-like object. 
            # Filter the videos manually if we can't search purely by video
            logger.info(f"Found {len(response)} asset(s) in ImageKit.")
            for item in response:
                title = item.name
                # Try to parse title from tags
                if hasattr(item, 'tags') and item.tags:
                    for tag in item.tags:
                        if tag.startswith('title:'):
                            title = tag.replace('title:', '', 1)
                            break
                            
                videos.append({
                    "id": item.file_id,
                    "url": item.url,
                    "title": title,
                    "name": item.name
                })
            return videos
        except Exception as e:
            logger.error(f"Error listing video files from ImageKit: {e}", exc_info=True)
            return []


# =====================================================================
# INTERACTIVE DESKTOP TESTING MAIN
# =====================================================================
if __name__ == "__main__":
    import tkinter as tk
    from tkinter import filedialog

    # 1. Instantiate the manager
    manager = IMAGEKIT_VIDEO_MANAGER()
    
    # 2. Check if the user forgot to replace the placeholder key
    if manager.private_key == "your_private_api_key":
        print("❌ CRITICAL: Testing aborted. Please edit video_manager.py and add your actual ImageKit private key.")
        sys.exit(1)

    # 3. Initialize and hide the Tkinter GUI window shell
    root = tk.Tk()
    root.withdraw()
    
    print("Opening file picker... Please select a video file.")
    
    # 4. Open native operating system window file picker
    file_path = filedialog.askopenfilename(
        title="Select a Small Video to Upload to ImageKit",
        filetypes=[("Video Files", "*.mp4 *.mov *.avi *.mkv"), ("All Files", "*.*")]
    )
    
    if file_path:
        print(f"\n[Selected File]: {file_path}")
        print("Uploading to ImageKit... (Please wait while stream processes)")
        
        # 5. Execute upload method
        upload_res = manager.upload_video(file_path)
        
        if upload_res and "url" in upload_res:
            print("\n✅ UPLOAD SUCCESSFUL!")
            print(f"Returned Video Link: {upload_res.get('url')}")
            uploaded_id = upload_res.get('fileId')
            print(f"Returned File ID  : {uploaded_id}")
            
            # 6. Execute fetch list verification method
            print("\n--- Testing Fetch All Video Links ---")
            links = manager.fetch_all_videos_link()
            print(f"Total Cloud Video Assets Found: {len(links)}")
            print(f"URLs currently in cloud accounts: {links}")
            
            # 7. Ask user if they want to clean up and delete the test video
            print("\n------------------------------------------------")
            cleanup = input("Do you want to test deletion of this video asset right now? (y/n): ").strip().lower()
            if cleanup == 'y':
                print("Deleting video asset...")
                del_res = manager.delete_video(uploaded_id)
                print(f"Final Delete Status: {del_res}")
            else:
                print("Skipping deletion. The video will remain active in your ImageKit dashboard.")
                
        else:
            print("\n❌ Upload process failed. Verify your ImageKit credentials or check file size constraints (Max 25MB for free tier).")
    else:
        print("\n🚫 Upload cancelled. No file was selected.")