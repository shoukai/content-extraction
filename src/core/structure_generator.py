import os
import json
from loguru import logger
from src.core.generator import generator

def generate_book(project_name: str, fragments_dir: str, output_file: str):
    """
    基于 TOC 和片段生成最终书籍
    """
    if not os.path.exists(fragments_dir):
        logger.error(f"Fragments directory {fragments_dir} not found.")
        return

    if not generator:
        logger.error("Generator not initialized.")
        return
    
    # Try to load dynamic TOC first
    toc_path = os.path.join(os.path.dirname(fragments_dir), "toc_raw.json")
    toc = None
    if os.path.exists(toc_path):
        logger.info(f"Loading dynamic TOC from {toc_path}")
        with open(toc_path, 'r', encoding='utf-8') as f:
            toc = json.load(f)
    else:
        logger.info(f"Using static TOC definition for {project_name}")
        from src.utils.toc_definitions import get_toc
        toc = get_toc(project_name)
        
    if not toc:
        logger.error(f"No TOC found for project: {project_name}")
        return

    logger.info(f"Generating structured document for {project_name} using Generator core logic...")
    
    try:
        content = generator.generate_from_structure(toc, fragments_dir)
        
        # Add Title and Intro
        final_content = f"# {project_name.capitalize()} Official Guide (Structured)\n\n"
        final_content += "> Document generated via Content Extraction Pipeline based on official TOC.\n\n"
        final_content += content
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(final_content)
            
        logger.success(f"Done! Written to {output_file}")
        
    except Exception as e:
        logger.error(f"Error during generation: {e}")
