import datetime

def find_year(numeric_string: int) -> list[int]:
    """
    Searches a numeric string for any four-digit sequences that represent
    valid years from 2000 up to the current year.

    Args:
        numeric_string: The integer number to search within.

    Returns:
        A list of valid years found within the numeric string.
    """
    str_num = str(numeric_string)
    found_years = []
    current_year = datetime.datetime.now().year # Current year is 2025

    # Iterate through the string, looking for 4-digit substrings
    for i in range(len(str_num) - 3): # -3 because we need at least 4 characters for a year
        potential_year_str = str_num[i:i+4]
        
        # Check if the substring is composed entirely of digits
        if potential_year_str.isdigit():
            potential_year = int(potential_year_str)
            
            # Validate if it's a year between 2000 and the current year
            if 2000 <= potential_year <= current_year:
                found_years.append(potential_year)
                
    # Return unique years found (in case of duplicates like '20232023')
    found_years = sorted(list(set(found_years)))
    if len(found_years) > 0:
        return int(found_years[0])
    else:
        return None

