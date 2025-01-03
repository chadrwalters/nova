"""Create a test PDF file for Nova testing."""
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pathlib import Path

def create_test_pdf():
    """Create a simple test PDF with text and basic formatting."""
    output_path = Path(__file__).parent / "sample.pdf"
    
    # Create PDF
    c = canvas.Canvas(str(output_path), pagesize=letter)
    
    # Add title
    c.setFont("Times-Bold", 24)
    c.drawString(1*inch, 10*inch, "Test Document")
    
    # Add body text
    c.setFont("Times-Roman", 12)
    c.drawString(1*inch, 9*inch, "This is a test PDF document for Nova's document handling tests.")
    
    # Add some formatted text
    c.setFont("Times-Bold", 14)
    c.drawString(1*inch, 8*inch, "Features:")
    
    c.setFont("Times-Roman", 12)
    y = 7.5
    for feature in [
        "Basic text formatting",
        "Multiple lines of text",
        "Font variations",
        "Simple layout"
    ]:
        c.drawString(1.5*inch, y*inch, "• " + feature)
        y -= 0.5
    
    # Add footer
    c.setFont("Times-Roman", 10)
    c.drawString(1*inch, 1*inch, "Created for Nova test suite")
    
    # Save the PDF
    c.save()

if __name__ == "__main__":
    create_test_pdf() 