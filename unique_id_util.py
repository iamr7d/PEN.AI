import uuid

def generate_unique_id():
    """Generate a unique UUID4 string."""
    return str(uuid.uuid4())

if __name__ == "__main__":
    print(generate_unique_id())
