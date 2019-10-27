def read_until_line_containing(reader, targetStr):
    """keeps running readline() with the provided reader until a line with the targetStr is found or the stream ends"""
    line = reader.readline()
    
    while targetStr not in line and line != '':
        line = reader.readline()
        
    return line
        