# simple shared file utility functions

def read_file_to_linearray(filename):
    lines = []
    with open(filename, "r") as f:
        for line in f:
            lines.append(line)
    return lines

def write_file_from_linearray(array, filename):
    with open(filename, "w") as f:
        for line in array:
            f.write(line)