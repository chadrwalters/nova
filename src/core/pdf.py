from weasyprint.text.fonts import FontConfiguration
from weasyprint.fonts import FontConfiguration
import gc
import os

class PDFGenerator:
    def __init__(self):
        self.font_config = FontConfiguration()
        self._initialize_fonts()
        
        self.font_config.subset_options = {
            'layout_features': ['kern', 'liga', 'rlig'],
            'skip_missing': True
        }

    def _initialize_fonts(self):
        """Initialize font configuration."""
        # Use system font configuration
        self.font_config = FontConfiguration()
        
        # Set default fallback chain
        self.font_config.default_font_family = "Helvetica"
        self.font_config.fallback_font_families = [
            "Arial",
            "Liberation Sans",
            "DejaVu Sans"
        ]

    def process_hr_element(self, element):
        """Process horizontal rule element."""
        try:
            # Create a simple horizontal rule
            return {
                'type': 'hr',
                'style': {
                    'border-top': '1px solid black',
                    'margin': '1em 0'
                }
            }
        except ValueError as e:
            self.logger.warning(f"Failed to process HR element: {e}")
            # Return a simple line as fallback
            return {
                'type': 'hr',
                'style': {
                    'border-top': '1px solid black',
                    'margin': '1em 0'
                }
            }

    def draw_horizontal_line(self, width: int, style: str, color: str):
        """Draw a horizontal line with specified properties."""
        # Implementation depends on your PDF library
        pass

    def __cleanup_memory(self):
        """Force memory cleanup."""
        gc.collect()
        gc.collect()  # Second pass to clean up circular references

    def generate_pdf(self, content, output_path):
        try:
            self.__cleanup_memory()
            
            # Set memory-efficient options
            self.font_config.subset = True  # Enable font subsetting
            self.font_config.optimize_size = True
            
            result = self._generate_pdf_content(content)
            self.__cleanup_memory()
            
            # Write to file
            with open(output_path, 'wb') as f:
                f.write(result)
                
        finally:
            # Final cleanup
            self.__cleanup_memory()