import os
from loguru import logger
from src.core.generator import generator
from src.utils.toc_definitions import LANGCHAIN_TOC

def generate_book(fragments_dir: str, output_file: str):
    """
    基于 TOC 和片段生成最终书籍
    """
    if not os.path.exists(fragments_dir):
        logger.error(f"Fragments directory {fragments_dir} not found.")
        return

    if not generator:
        logger.error("Generator not initialized.")
        return
    
    logger.info("Generating structured document using Generator core logic...")
    
    try:
        content = generator.generate_from_structure(LANGCHAIN_TOC, fragments_dir)
        
        # Add Title and Intro
        final_content = "# LangChain Official Guide (Structured)\n\n"
        final_content += "> Document generated via Content Extraction Pipeline based on official TOC.\n\n"
        final_content += content
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(final_content)
            
        logger.success(f"Done! Written to {output_file}")
        
    except Exception as e:
        logger.error(f"Error during generation: {e}")
