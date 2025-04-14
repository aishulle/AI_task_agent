def fibonacci_sequence(limit):
    """
    Generates a Fibonacci sequence up to a given limit.

    Args:
        limit: The upper limit for the sequence.

    Returns:
        A list containing the Fibonacci sequence up to the limit.
    """
    a, b = 0, 1
    sequence = []
    while a <= limit:
        sequence.append(a)
        a, b = b, a + b
    return sequence

if __name__ == "__main__":
    try:
        limit = 100
        sequence = fibonacci_sequence(limit)
        print(sequence)

    except Exception as e:
        print(f"An error occurred: {e}")

