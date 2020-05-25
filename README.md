# whatsapp-analytics

Data analytics for a WhatsApp group chat history. Export a WhatsApp chat history from a group you are a member of and run exploratory data analysis on it. A preprocessor script wrangles the data to make it amenable for analytics application and creates a metadata YAML file with basic information about the group. The analytics is performed by an R Jupyter notebook. The analysis provides insights such as timeseries for message frequency, frequent senders and correlation between message sending patterns of various members.

## Exporting chat history from a WhatsApp group

I did this on an Android phone but should be similar on others as well. Get a dump of the chat history of a WhatsApp group requires you to be a member of that group. On the top right corner press the icon for the three dots, then select more and then select export chat. This will allow you to email a text file of the chat history. Once you have the chat history file in the email, you have the raw data we need for this analysis.

## Preprocessing the raw data

The raw data file exported from WhatsApp is not amenable for analysis, an example is presented below:

```{bash}
1/6/20, 11:26 AM - Jane: Judy do you have plans for the 13th 🤔?
```

What we want is a CSV file in the following format:

```{bash}
date,timestamp,sender,message,emojis
"1/6/20","1/6/20 11:26 AM","Jane","Judy do you have plans for the 13th 🤔?","🤔"
```

The preprocess.py script converts the raw data into preprocessed data via the following command line:

```{bash}
python preprocess.py usage: preprocess.py [-h] --raw-data-filename RAW_DATA_FILENAME [--group-name GROUP_NAME] [--sender-name-map SENDER_NAME_MAP]

optional arguments:
  -h, --help            show this help message and exit
  --raw-data-filename RAW_DATA_FILENAME
                        Name of the file containing the raw data as exported from WhatsApp
  --group-name GROUP_NAME
                        Group name to use if not found in the data or if the name in the data needs to be overridden
  --sender-name-map SENDER_NAME_MAP
                        json dictionary as a string containing name mappings, e.g. '{"buddy": "John Doe","whothis": "Jane Doe"}'

# Example
python preprocess.py --raw-data-filename raw_data_from_whatsapp.txt --group-name "My Group" --sender-name-map '{"Bestie": "Jane Doe"}'
```

The preprocessor script generates the output CSV file as well as YAML file containing some metadata about the group such as when was this group created, by whom, message count per sender etc. A sample YAML file is presented below:

```{bash}
created_by: Jane Doe
creation_date: 4/30/19
date_when_most_messages_were_sent: 3/2/20
events:
- 1/1/20, 9:33 PM - Messages to this group are now secured with end-to-end encryption.
  Tap for more info.
- 4/30/19, 12:45 PM - Jane Doe created group "Friends for life"
- 1/1/20, 9:33 PM - Judy added you
- 1/14/20, 12:17 AM - Jane Doe changed this group's icon
group_name: Friends for life
median_message_count_per_day: 33
members:
- message_count: 488
  name: Polly
- message_count: 1139
  name: Rebecca
- message_count: 1790
  name: Jane Doe
- message_count: 1437
  name: Samantha
- message_count: 929
  name: Julia
- message_count: 253
  name: Steven
- message_count: 384
  name: Scott
- message_count: 149
  name: Duke Kent
most_active_sender: Jane Doe
```

## Data Analysis

Refer to the Jupyter notebook for data analysis. A subset of questions that the notebook answers is as follows:

1. Timeseries for messages per day, a non-parametric fit for it. This is explored overall for the entire group as well as for each sender.

2. Do more messages occur on certain days of the week? Hour of day?

3. Correlation between message sending pattern for individual senders.

4. Length of message per sender.

5. Frequently occuring words.

## Sample datasets

There are some WhatsApp datasets available online, you can find them via a Google search. I am not providing the link here due to privacy concerns. I could find [this paper](https://users.ics.aalto.fi/kiran/content/whatsapp.pdf) and [associated github](https://github.com/gvrkiran/whatsapp-public-groups) repo as well which presents results from analysing a large number of WhatsApp datasets.


## Ethics Note

The code and analysis provided here is for academic purposes only. Please understand what you are doing before doing any of the stuff mentioned above. Use the tools mentioned above at your own risk. The author(s) of this code do not take any responsibility.

