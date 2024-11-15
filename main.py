import os
import tempfile
import zipfile

from bs4 import BeautifulSoup


def extract_epub_to_temp(epub_path):
    temp_dir = tempfile.TemporaryDirectory()
    with zipfile.ZipFile(epub_path, "r") as zf:
        zf.extractall(temp_dir.name)
    return temp_dir


def find_content_opf(temp_dir):
    container_path = os.path.join(temp_dir, "META-INF", "container.xml")
    with open(container_path, "r", encoding="utf-8") as file:
        container_xml = file.read()
    soup = BeautifulSoup(container_xml, "xml")
    content_opf_path = soup.find("rootfile")["full-path"]
    return os.path.join(temp_dir, content_opf_path)


def parse_content_opf(content_opf_path):
    with open(content_opf_path, "r", encoding="utf-8") as file:
        opf_content = file.read()
    soup = BeautifulSoup(opf_content, "xml")

    manifest = {item["id"]: item["href"] for item in soup.find_all("item")}
    spine = [itemref["idref"] for itemref in soup.find_all("itemref")]

    return manifest, spine


def map_spine_to_files(manifest, spine, base_path):
    spine_files = [os.path.join(base_path, manifest[item_id]) for item_id in spine]
    return spine_files


def get_spine_xml_position(content_opf_path):
    """Find the <spine>'s index in the XML document tree."""
    with open(content_opf_path, "r", encoding="utf-8") as file:
        opf_content = file.read()
    soup = BeautifulSoup(opf_content, "xml")

    # Find all top-level elements under <package>
    package_children = soup.find("package").find_all(recursive=False)
    for idx, child in enumerate(package_children):
        if child.name == "spine":
            return idx + 1, len(package_children)  # 1-based index
    return -1, len(package_children)  # Fallback if <spine> not found


def traverse_and_trace_query(spine_files, query):
    for spine_idx, file_path in enumerate(spine_files):
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
        soup = BeautifulSoup(content, "html.parser")
        element_with_query = None
        match_start = -1
        match_end = -1

        # Search for the query in the content
        for element in soup.find_all(string=True):  # Search through all text nodes
            if query in element:
                element_with_query = element
                match_start = element.find(query)
                match_end = match_start + len(query)
                break

        if element_with_query:
            # Trace the element tree path and calculate file index
            element_path = []
            file_index = []
            current_element = element_with_query.parent
            while current_element:
                siblings = current_element.find_previous_siblings(current_element.name)
                element_position = len(siblings) + 1
                element_path.append(f"{current_element.name}[{element_position}]")

                # Add to file_index only if the current element is not <html>
                if current_element.name != "html":
                    file_index.insert(
                        0, element_position
                    )  # Build the file index as a list

                current_element = current_element.parent
            element_path.reverse()

            # Format the file index as a hierarchical path (e.g., "2/3/1")
            file_index_str = "/".join(map(str, file_index))

            return (
                spine_idx + 1,  # 1-based spine index
                len(spine_files),
                file_path,
                "/".join(element_path),
                file_index_str,
                match_start,
                match_end,
            )

    print("Query not found in the spine.")
    return None, None, None, None, None, -1, -1


def process_epub(epub_path, query):
    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(epub_path, "r") as zf:
            zf.extractall(temp_dir)

        content_opf_path = find_content_opf(temp_dir)
        manifest, spine = parse_content_opf(content_opf_path)
        spine_files = map_spine_to_files(
            manifest, spine, os.path.dirname(content_opf_path)
        )

        # Get spine's position in the XML tree
        spine_xml_position, total_xml_elements = get_spine_xml_position(
            content_opf_path
        )

        (
            spine_idx,
            total_spines,
            matching_file,
            element_path,
            file_index,
            start_offset,
            end_offset,
        ) = traverse_and_trace_query(spine_files, query)

        if matching_file:
            print(f"Matching file: {matching_file}")
            print(f"Spine index: {spine_xml_position}/{spine_idx}")
            print(f"File index: {file_index}")
            print(f"Element path: {element_path}")
            print(f"Match start: {start_offset}")
            print(f"Match end: {end_offset}")
        else:
            print("Query not found.")


if __name__ == "__main__":
    epub_query = """rklı mefhumlardır. Dünyevî kültür ne demek? Kül"""
    epub_path = "x.epub"  # Replace with your EPUB file path
    process_epub(epub_path, epub_query)
