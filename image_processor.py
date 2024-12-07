from transformers import CLIPProcessor, CLIPModel
import torch
from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel


class ImageProcessor:
    def __init__(self, model_name="openai/clip-vit-base-patch32"):
        self.model = CLIPModel.from_pretrained(model_name)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.model.eval()

    def process_image(self, image_file):
        try:
            image = Image.open(image_file).convert("RGB")
            inputs = self.processor(images=image, return_tensors="pt")

            with torch.no_grad():
                outputs = self.model.get_image_features(**inputs)

            embedding = outputs / outputs.norm(p=2, dim=-1, keepdim=True)  # L2 정규화
            return embedding.squeeze().tolist()

        except Exception as e:
            print(f"Error in process_image: {e}")
            return None
