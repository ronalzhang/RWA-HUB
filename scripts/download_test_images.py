import os
import requests

# 图片URL列表
image_urls = {
    "building1.jpg": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab",
    "building2.jpg": "https://images.unsplash.com/photo-1478860409698-8707f313ee8b",
    "building3.jpg": "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00",
    "building4.jpg": "https://images.unsplash.com/photo-1512917774080-9991f1c4c750",
    "building5.jpg": "https://images.unsplash.com/photo-1495379572396-5f27a279ee91",
    "interior1.jpg": "https://images.unsplash.com/photo-1497366754035-f200968a6e72",
    "interior2.jpg": "https://images.unsplash.com/photo-1497366811353-6870744d04b2",
    "interior3.jpg": "https://images.unsplash.com/photo-1497366216548-37526070297c",
    "aerial1.jpg": "https://images.unsplash.com/photo-1473163928189-364b2c4e1135",
    "aerial2.jpg": "https://images.unsplash.com/photo-1506146332389-18140dc7b2fb"
}

def download_images():
    # 确保目录存在
    image_dir = "app/static/test_images"
    os.makedirs(image_dir, exist_ok=True)
    
    # 下载每张图片
    for filename, url in image_urls.items():
        filepath = os.path.join(image_dir, filename)
        print(f"Downloading {filename}...")
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            with open(filepath, "wb") as f:
                f.write(response.content)
            
            print(f"Successfully downloaded {filename}")
        except Exception as e:
            print(f"Failed to download {filename}: {str(e)}")

if __name__ == "__main__":
    download_images() 