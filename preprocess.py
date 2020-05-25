"""
Preprocess exported data from WhatsApp. The WhatsApp data export is messy, this app creates a nice
CSV file of the format "date,timestamp,sender,message" which can then be consumed by downstream
applications to do data analysis. A sample line from a WhatsApp export (this is as of May 25, 2020)
looks like this:
1/6/20, 11:26 AM - Jane: How is everyone today?

The main preprocessing steps done here are:
1. Convert multiline messages into a single line message.
2. Extract sender name and also support a sender name map which could be used for anonymizing data.
3. Create a timestamp field with data and timestamp information.
4. Creates a metadata YAML file that includes information such as when was this group created, total
   number of messages, total number of unique senders etc.
"""
import re
import sys
import json
import yaml
import emoji
import logging
import argparse
import pandas as pd
from dateutil.parser import parse

# global constants
APP_NAME = "preprocess"
CSV_HEADER = "date,timestamp,sender,message,emojis\n"
MIN_EXPECTED_TOKENS = 6
TEMP_FILE = "temp.txt"
CREATED_GROUP_STRING = "created group"
GROUP_NAME_UNKNOWN = "unknown"

'''
All logging is to stderr. This allows us to pipe the output of commands through other
processes without the logging interfering.
'''
logging.basicConfig(format='%(asctime)s,%(module)s,%(funcName)s,%(lineno)d,%(levelname)s,%(message)s', level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


# ===============================================================================

def extract_emojis(s):
  return ','.join(c for c in s if c in emoji.UNICODE_EMOJI)


def is_date(string, fuzzy=False):
    """
    Return whether the string can be interpreted as a date.

    :param string: str, string to check for date
    :param fuzzy: bool, ignore unknown tokens in string if True
    """
    try: 
        parse(string, fuzzy=fuzzy)
        return True

    except ValueError:
        return False


def parse_args():
    # create the main top-level parser
    top_parser = argparse.ArgumentParser()
    
    # Common parameters for produce and consume sub-commands
    top_parser = argparse.ArgumentParser(add_help=True)
    top_parser.add_argument(
        '--raw-data-filename',
        dest='raw_data_filename',
        type=str,
        required=True,
        help='Name of the file containing the raw data as exported from WhatsApp')

    top_parser.add_argument(
        '--group-name',
        dest='group_name',
        type=str,
        required=False,
        help='Group name to use if not found in the data or if the name in the data needs to be overridden')
        
    top_parser.add_argument(
        '--sender-name-map',
        dest='sender_name_map',
        type=str,
        required=False,
        help='json dictionary as a string containing name mappings, e.g. \'{\"buddy\": \"John Doe\",\"whothis\": \"Jane Doe\"}\'')
        
    if len(sys.argv) == 1:
        top_parser.print_help(sys.stderr)
        sys.exit(1)
    return top_parser.parse_args()

def main():
    """
    Top level application logic
    """
    args = parse_args()
    logger.info(f"{APP_NAME} starting...")
    logger.info(args)

    # convert the sendermap to a dictionary
    sender_map = {} if args.sender_name_map is None else json.loads(args.sender_name_map)
    
    logger.info(f"going to read raw data from {args.raw_data_filename}")
    with open(args.raw_data_filename, 'r') as f:
        # some messages are multiline and that breaks the parsing for
        # downstream apps, so we want to convert these multiline messages
        # into long single line messages. We do this by removing the newline char
        # from the line just preceding the 2nd, 3rd..nth line of a multiline message.
        remove_newline_for_these_lines = []
        index = 0
        
        # all lines in the file
        all_lines = []

        # read file line by line
        for line in f:
            # old format of the WhatsApp Chat export created lines like this
            # 21/12/16, 11:48:42 PM: Some Body: How are you?
            # we want to convert this as the rest of the code works with that format
            # 21/12/16, 11:48:42 PM - Some Body: How are you?
            line  = line.replace("AM:", "AM -")
            line  = line.replace("PM:", "PM -")

            # split into tokens, only the first one is date, rest are not of interest at this time
            tokens = line.split(",")

            # if the first token is not a date then this the nth line of a multiline message
            # as new message lines always start with a date
            if is_date(tokens[0]) is False:
                if index != 0:
                    remove_new_lines_from_line = index-1
                    remove_newline_for_these_lines.append(remove_new_lines_from_line)
                    logger.info(f"line \"{line}\" does not start with a date, going to remove newlines from line {remove_new_lines_from_line}")
            index += 1
            all_lines.append(line)

        logger.info(f"there are {len(remove_newline_for_these_lines)} from which newline needs to be removed")    
        for i in remove_newline_for_these_lines:
            all_lines[i] = all_lines[i].replace("\n", "")
        
        # join all the lines again to one large string which we will write to a file
        # the idea here is to reread that temp file so that now all multiline messages are
        # gone and we have one message per line which we can easily handle
        all_lines = "".join(all_lines)
        with open(TEMP_FILE, "w") as f:
            f.write(all_lines)
        
    
    # create a cleanly formatted CSV line list out of this
    # example: 1/6/20, 11:26 AM - John Doe: Jane let me know your plans for the 13th
    csv_lines = []
    first_line = True
    with open(TEMP_FILE, 'r') as f:
        all_lines = f.readlines()

    # we finally have a list containing single line messages
    index = 1
    # dictionary for metadata information
    group_info = {'events': [], 'members': []}
    for l in all_lines:
        # each line looks like this
        # 1/6/20, 11:26 AM - John Doe: Jane let me know your plans for the 13th
        # combine tokens 1 through 4 to create a timestamp
        tokens = l.split(" ")

        # the second line contains the group and creator name
        if index == 1:
            if CREATED_GROUP_STRING in l:
                # 4/30/19, 12:45 PM - Jane Doe created group "Friends for life"
                group_info['creation_date'] = tokens[0][:-1]
                if tokens[5] == "created" and tokens[6] == "group":
                    group_info['created_by'] = tokens[5]
                    logger.info(f"tokens={tokens}")
                    group_info['group_name'] = args.group_name if args.group_name is not None else " ".join(tokens[7:]).replace("\"", "")
                        
                elif tokens[6] == "created" and tokens[7] == "group":
                    group_info['created_by'] = f"{tokens[4]} {tokens[5]}"
                    group_info['group_name'] = args.group_name if args.group_name is not None else " ".join(tokens[8:]).replace("\"", "")
            else:
                logger.error(f"seems like the second line does not contain group creation info")
                logger.error(f"second line=\"{l}\"")
                group_info['group_name'] = args.group_name if args.group_name is not None else GROUP_NAME_UNKNOWN
                logger.info(f"set group name to {group_info['group_name']}")
                

        # if this line is misformatted then exit, we believe we have all formats of lines
        # in the WhatsApp chat export handled, if not then we dont want to continue and
        # fix the code first
        if len(tokens) < MIN_EXPECTED_TOKENS:
            logger.error(f"line=\"{l}\" has less than then minimum expected number of tokens {MIN_EXPECTED_TOKENS}, skipping it")
            logger.error("CODE FIX NEEDED....")
            sys.exit(0)
        
        # first token is date, remove the "," at the end
        date = tokens[0][:-1]

        # combine the first 3 tokens to create a timestamp
        timestamp = f"{tokens[0][:-1]} {tokens[1]} {tokens[2]}"

        # the sender could be one name or first name and last name
        ti = 4
        found_colon = False
        for t in tokens[4:]:
            if t.endswith(":"):
                logger.info(f"found : in token {ti}, token={t}")
                found_colon = True
                break
            else:
                logger.info(f"did not find : in token {ti}, token={t}")

            ti += 1
        if found_colon is True:
            sender = " ".join(tokens[4:ti+1])[:-1]
            message_start_at_token = ti + 1
        else:
            # this is probably an event like someone changing the group name
            # or adding someone to the group
            group_info['events'].append(l.replace("\n", ""))
            # if this was the first line then ok to have no sender since it typically
            # 1/1/20, 9:33 PM - Messages to this group are now secured with end-to-end encryption. Tap for more info.
            if first_line is False:
                logger.info("did not find : so could not determine sender, skipping")
                logger.info(f"problem line was \"{l}\"")
                first_line = False
                continue
            else:
                logger.info("skipped past first line")
                first_line = False
                continue
        
        # if we want to call the sender by a different name, this is needed if you have the person by
        # a nickname in your phonebook
        sender = sender_map.get(sender, sender)

        # count of messages per user
        m = [m for m in group_info['members'] if m['name'] == sender]
        if len(m) != 0:
            m[0]['message_count'] += 1
        else:
            logger.info(f"adding member {sender} to the metadata")
            group_info['members'].append({'name': sender, 'message_count': 0})

        # join the date, timestamp, sender and message into a CSV line   
        message = " ".join(tokens[message_start_at_token:]).replace("\n", "").replace("\"", "")

        # extract the emojis from this message line
        emojis = extract_emojis(message)
        
        # create the csv line
        csv_line = f"\"{date}\",\"{timestamp}\",\"{sender}\",\"{message}\",\"{emojis}\"\n"
        csv_lines.append(csv_line)
        first_line = False
        index += 1

    # write the processed data to output file
    output_file = f"preprocessed_{args.raw_data_filename}"
    with open(output_file, 'w') as f:
        f.write(CSV_HEADER)
        for l in csv_lines:
            f.write(l)
    logger.info(f"all data written to {output_file}")

    # do some basic EDA and put the results group info dictionary
    df = pd.read_csv(output_file)
    logger.info(df)
    # most active member
    group_info['most_active_sender'] = df['sender'].value_counts().index[0]
    group_info['date_when_most_messages_were_sent'] = df['date'].value_counts().index[0]
    group_info['median_message_count_per_day'] = int(df['date'].value_counts().quantile(q=0.5))

    # write the YAML file with the metadata
    logger.info(json.dumps(group_info, indent=2))
    output_file = f"metadata_{args.raw_data_filename}"
    logger.info(f"going to write the metadata to the yaml file {output_file}")
    with open(output_file, 'w') as metadata_yaml_file:
        yaml.dump(group_info, metadata_yaml_file)

    logger.info(f"All done")


###########################################################
# MAIN
###########################################################

if __name__ == '__main__':
    main()
