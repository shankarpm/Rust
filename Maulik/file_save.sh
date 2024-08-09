# Set a variable named today to the current date in the format YYYY-MM-DD
today=`date +%Y-%m-%d`;

# Find CSV files modified within the last 7 days, duplicate each line, and redirect the output to a combined file
find log_files/*csv -mtime -7 -exec awk 1 {} \; > log_files/combined_files/weekly_logs_$today.csv

# Check if the combined file is empty and append a message if so
[ -s log_files/combined_files/weekly_logs_$today.csv ] || echo "No app usage this week" >> log_files/combined_files/weekly_logs_$today.csv

# Delete CSV files modified within the last 7 days if they exist
find log_files/ -maxdepth 1 -name "*.csv" -mtime -7 -exec rm {} \;