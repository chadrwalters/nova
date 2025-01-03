"""Create test image files for Nova testing."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

def create_test_image():
    """Create a simple test image with text and shapes."""
    output_path = Path(__file__).parent / "test.jpg"
    
    # Create a new image with a white background
    width = 800
    height = 600
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    # Draw some shapes
    # Rectangle
    draw.rectangle([(50, 50), (750, 550)], outline='black', width=2)
    
    # Circle
    draw.ellipse([(300, 200), (500, 400)], outline='blue', width=2)
    
    # Lines
    draw.line([(100, 100), (700, 500)], fill='red', width=3)
    draw.line([(700, 100), (100, 500)], fill='green', width=3)
    
    # Add text
    draw.text((width//2, 100), "Test Image", fill='black', anchor='mm')
    draw.text((width//2, height-50), "Created for Nova test suite", fill='gray', anchor='mm')
    
    # Save the image
    image.save(output_path, quality=95)
    
    # Also save as PNG for comparison
    image.save(output_path.with_suffix('.png'))

if __name__ == "__main__":
    create_test_image() 