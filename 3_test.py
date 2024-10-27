import pandas as pd
import numpy as np
import json
from edgar import *
from tqdm import tqdm
from joblib import Parallel, delayed
import pickle
import re
import multiprocessing
set_identity('8049qq.com@gmail.com')
# soft freeze pattern 1
verbs_1 = ['new employee', 'new participant', 'new entrant', 'new associate', 'Hired after','new plan participants', 'new participation', 'new hires']
nouns_1 = ['defined benefit', 'pension plan', 'retirement', 'postretirement', 'postemployment', 'pension', 'benefit']

# Create a regex pattern
pattern_1 = r'\b(?:' + '|'.join(re.escape(word) for word in verbs_1) + r')\b(?:\W+\w+){0,15}?\W+\b(?:' + '|'.join(re.escape(word) for word in nouns_1) + r')\b' + \
            r'|\b(?:' + '|'.join(re.escape(word) for word in nouns_1) + r')\b(?:\W+\w+){0,15}?\W+\b(?:' + '|'.join(re.escape(word) for word in verbs_1) + r')\b'


# for pattern 2
verbs_2 = ['move', 'moved', 'transfer', 'transferred', 'transfering', 'transfered', 'transfering', 'transfered' ,'transit', 'transition','transited','change','changed','turn','turned','new employee']
nouns_2 = ['defined benefit', 'pension plan', 'retirement', 'postretirement', 'defined contribution', 'contribution', '401(k)']

# pattern 2
pattern_2 = r'\b(?:' + '|'.join(re.escape(word) for word in verbs_2) + r')\b(?:\W+\w+){0,20}?\W+\b(?:' + '|'.join(re.escape(word) for word in nouns_2) + r')\b' + \
            r'|\b(?:' + '|'.join(re.escape(word) for word in nouns_2) + r')\b(?:\W+\w+){0,20}?\W+\b(?:' + '|'.join(re.escape(word) for word in verbs_2) + r')\b'




for year in tqdm(range(1994,2025)):

    # open pcikle file to get the freeze collection
    with open(f'soft freeze/freeze_collection_{year}.pkl', 'rb') as f:
        freeze_collection = pickle.load(f)



    freeze_all = {}
    # loop through the freeze collection, key is the filing, value is (result 1, result 2)
    for key, value in freeze_collection.items():

        # for each filing, we store the filing information first
        file_info = {'form': key.form,
                    'date': key.filing_date,
                    'cik': key.cik,
                    'company': key.company,
                    'link': key.document.url
                    }
        
        # for each filing, there are results 1 and 2 which may contain multiple sections
        result_1 = {}
        if (value[0] is not None and value[0]['sections']): # if there is a result 1
            for n, section in enumerate(value[0]['sections']): # loop through each section
                # identify whether the section is a table, if there is too much "|" in the section, then it is a table
                if section['doc'].count('|') > 20:
                    continue

                # find the keywords in the section
                matches_1 = re.findall(pattern_1, section['doc'], re.IGNORECASE)
                serp_search = re.search('SERP', section['doc'], re.IGNORECASE)

                if serp_search:
                    serp_index = 1
                else:
                    serp_index = 0
                
                # store the section information
                section_dict = {
                    'doc' : section['doc'],
                    'keywords': matches_1,
                    'serp': serp_index
                }
                
                result_1[f'section_{n}'] = section_dict
            
        
        # same for results 2
        result_2 = {}
        if (value[1] is not None and value[0]['sections']):
            for n, section in enumerate(value[1]['sections']):
                if section['doc'].count('|') > 20:
                    continue

                matches_2 = re.findall(pattern_2, section['doc'], re.IGNORECASE)
                
                
                section_dict = {
                    'doc' : section['doc'],
                    'keywords': matches_2
                }
                
                result_2[f'section_{n}'] = section_dict


    #    if both results are empty, then we don't need to store this record
        if not result_1 and not result_2:
            continue

        freeze_all[key.accession_no] = {
            'file_info': file_info,
            'result_1': result_1,
            'result_2': result_2
        }



    with open(f'processed/summary_keywords_{year}.pkl', 'wb') as f:
        pickle.dump(freeze_all, f)

    # transform the dictionary to a table for search 1
    table_all_1 = {}
    for key, value in freeze_all.items(): # key is filing accession no, value contains three part, file_info, result_1, result_2
        if not value['result_1']: # if there is no result 1, then try next
            continue

        col_dict = value['file_info'] # we get the file information first

        section_list = [] # store the section information in a list instead of a dictionary, so we can explode it later and turn it into a table
        for section, content in value['result_1'].items():
            section_list.append((content['doc'],content['keywords'], content['serp'])) # store the doc, keywords, and serp information

        col_dict['section'] = section_list

        table_all_1[key] = col_dict

    # exploe the section and keyword list, and turn it into a table
    table_1 = pd.DataFrame(table_all_1).T.explode('section')
    table_1[['doc', 'keyword','serp']]= table_1['section'].apply(pd.Series)
    table_1.drop(columns = ['section'], inplace = True)
    table_1.to_excel(f'processed/search1_result_{year}.xlsx')

    # # transform the dictionary to a table for search 2 
    # table_all_2 = {}
    # for key, value in freeze_all.items():
    #     if not value['result_2']:
#         continue

#     col_dict = value['file_info']

#     section_list = []
#     for section, content in value['result_2'].items():
#         section_list.append((content['doc'],content['keywords']))

#     col_dict['section'] = section_list
#     table_all_2[key] = col_dict

# # exploe the section and keyword list, and turn it into a table
# table_2 = pd.DataFrame(table_all_2).T.explode('section')
# table_2[['doc', 'keyword']]= table_2['section'].apply(pd.Series)
# table_2.drop(columns = ['section'], inplace = True)
# table_2.to_excel(f'data/search2_result_{year}_alternative.xlsx')
