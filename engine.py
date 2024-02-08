import multiprocessing
import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import string
import nltk
import time
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')
nltk.download('cmudict')
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import cmudict

folderpath = r'C:\Users/suwes/SentimentEngine/'
textfile_path = f"{folderpath}inputtext/"
stopword_path = f"{folderpath}StopWords/"
masterdict_path = f"{folderpath}MasterDictionary/"

def createdf():
  inputxlsx = os.path.join(folderpath, "Input.xlsx")
  dfxlsx = pd.read_excel(inputxlsx)
  print(dfxlsx)
  df_urls = dfxlsx['URL']
  #print(df_urls)
  return dfxlsx

df = createdf()

def extract(df):
  #extracting article text from urls
  def extract_urltext(url):
    response = requests.get(url)#send GET req to url
    soup = BeautifulSoup(response.content, 'html.parser')
    article_title = soup.find('title').get_text()#find and extract tile of article
    article_content = soup.find('div', class_= 'td-pb-span8 td-main-content')#find and extract article text
    article_text = ''
    if article_content:
      for para in article_content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        article_text += para.get_text()
    #print(article_title)
    #print(article_text)
    return article_title, article_text

  #url = 'https://insights.blackcoffer.com/rising-it-cities-and-its-impact-on-the-economy-environment-infrastructure-and-city-life-by-the-year-2040/'
  #extract_urltext(url)
  #article_title, article_text = extract_urltext(url)

  for index, row in df.iterrows():
    url = row['URL']
    url_id = row['URL_ID']
    article_title, article_text = extract_urltext(url)
    #save text to file
    filename = f"{folderpath}inputtext/{url_id}.txt"
    with open(filename, 'w', encoding = 'utf-8') as file:
      file.write(article_title+ '\n\n' +article_text)
    print(f"text saved to file {filename}")

#extract data
extract(df)

def transform(df):
  #cleaning stop words
  #reading stop words from stopword files
  def read_stopwords(stopword_folder):
    stopwords = set()
    filenames = os.listdir(stopword_folder)
    # process each file
    for filename in filenames:
      filepath = os.path.join(stopword_folder, filename)
      #read stop words from each file
      with open(filepath, 'r', encoding= 'utf-8', errors='ignore') as file:
        stopwords.update(map(str.strip, file.readlines()))
    return stopwords
  #stop words
  stopwords = read_stopwords(stopword_path) 

  #cleaning stop words from text
  def clean_stopwords(text, stopwords):
    #tokenize text
    words = word_tokenize(text)
    #remove stop words from text
    cleaned_words = [word for word in words if word.lower() not in stopwords]
    #reconstructing cleaned text
    cleaned_text = ' '.join(cleaned_words)
    return cleaned_text

  #cleaning stop words from a directory/multiple files
  def clean_stopwords_directory(directory, stopwords):
    #list all files in directory
    filenames = os.listdir(directory)
    #cleaning each file
    for filename in filenames:
      filepath = os.path.join(directory, filename)
      #read text from each file
      with open(filepath, 'r', encoding='utf-8', errors='ignore') as file:
        text = file.read()
      #clean stop words from file text
      cleaned_text = clean_stopwords(text, stopwords)
      #write back cleaned text
      with open(filepath, 'w', encoding= 'utf-8', errors='ignore') as file:
        file.write(cleaned_text)
      print(f"cleaned text from {filename}")

  clean_stopwords_directory(textfile_path, stopwords)
  #creating dictionary of positive and negative words
  def create_posneg_dict(masterdict_path, stopwords):
    poswords = set()
    negwords = set()
    #read positivewords file
    with open(os.path.join(masterdict_path, 'positive-words.txt'), 'r', encoding='utf-8', errors='ignore') as file:
      for line in file:
        words = line.strip().split()
        for word in words:
          if word.lower() not in stopwords:
            poswords.add(word.lower())
    #read negativewords file
    with open(os.path.join(masterdict_path, 'negative-words.txt'), 'r', encoding='utf-8', errors='ignore') as file:
      for line in file:
        words = line.strip().split()
        for word in words:
          if word.lower() not in stopwords:
            negwords.add(word.lower())
    return poswords, negwords

  positivewords, negativewords = create_posneg_dict(masterdict_path, stopwords)
  #print(positivewords)
  #print(negativewords)
  return stopwords, positivewords, negativewords

#cleaning/transforming data
stopwords, positivewords, negativewords = transform(df)

#load data
result_df = pd.DataFrame()
def loadoutput(folderpath, result_df):
  exceloutfilepath = f"{folderpath}Output.xlsx"
  result_df.to_excel(exceloutfilepath, index=False)
  print(f"output file saved to {exceloutfilepath}")
  print(f"analysis time: {int((time.time() - starttime)//3600)} hours {int(((time.time() - starttime)%3600)//60)} minutes {int((time.time() - starttime)%60)} seconds")

#process text files
def runengine(df, stopwords, files_subset, dflist):
  #sentimental analysis
  #calculating variables
  def calculate_positivescore(words, positivewords):
    positivescore = sum(1 for word in words if word.lower() in positivewords)
    return positivescore

  def calculate_negativescore(words, negativewords):
    negativescore = (sum(-1 for word in words if word.lower() in negativewords))*(-1)
    return negativescore

  #analysis of readability
  def calc_readibility(words, sentences):
    #calculate average length of sentences
    avg_sentencelen = len(words)/len(sentences) if sentences else 0
    #calculate % of complex words
    complexwords = [word for word in words if syllable_count(word)>2]
    percent_complexwords = len(complexwords)/len(words)*100 if words else 0
    #calculate fog index 
    fog_index = 0.4*(avg_sentencelen + percent_complexwords)
    return avg_sentencelen, percent_complexwords, fog_index

  #average words per text
  def avg_wordspersentence(words, sentences):
    if len(sentences) > 0:
      averagewords = len(words)/len(sentences)
      return averagewords
    else: return 0

  #complex word count
  def syllable_count(word):
      d = cmudict.dict()
      if word.lower() in d:
          return [len(list(y for y in x if y[-1].isdigit())) for x in d[word.lower()]][0]
      else:
          return 0
  def complexwords_count(words):
    complexwords = [word for word in words if syllable_count(word)>2]
    return len(complexwords)

  #clean words count 
  def cleanwords_count(words, stopwords):
    punctuations = set(string.punctuation)
    cleaned_words = [word.lower() for word in words if word.lower() not in stopwords and word.lower() not in punctuations]
    return len(cleaned_words)

  #syllable count per word
  #vowel syllable count per word
  def vowel_syllable(word):
    vowels = 'aeiouy'
    count = 0
    endings = 'es', 'ed', 'e'
    #exceptions for word with endings
    word = word.lower().strip()
    if word.endswith(endings):
      word = word[:-2]#subtract 2 characters from ending of word
    elif word.emdswith('le'):
      word = word[:-2]
      endings = ''
    elif word.endswith('ing'):
      word = word[:-3]#subtract 3 characters from ending of word
      endings = ''
    #counting vowels in word
    if len(word)<=3:
      return 1
    for index, letter in enumerate(word):
      if letter in vowels and (index ==0 or word[index -1] not in vowels):
        count +=1
    #handling y as vowel at end of word
    if word.endswith('y') and word[-2] not in vowels:
      count +=1
    return count
  #per text
  def vowel_syllable_perword(words):
    total_syllables = sum(syllable_count(word) for word in words)
    return total_syllables

  #personal pronouns
  def count_pronouns(text):
    pattern = r'\b(?:I|we|my|ours|us)\b'#define regex pattern for matching pronouns
    #find all matches
    matches = re.findall(pattern, text, flags=re.IGNORECASE)
    #excluse 'US' when reffering to USA
    matches_fin = [matches for match in matches if match.lower() != 'us']
    countpron = len(matches_fin)#count of pronouns
    return countpron

  #average word length
  def calc_avg_wordlength(words):
    total_chars = sum(len(word) for word in words)#calculate total charactes in text
    total_words = len(words)
    if total_words != 0:
      avg_wordlength = total_chars/total_words
    else: avg_wordlength = 0
    return avg_wordlength

  def appendtodf(url_idkey, calc_values, process_df):
    rowindex = df[df['URL_ID'] == url_idkey].index #get index of row where url_id = url_idkey
    if not rowindex.empty:
      idx_toupdate = rowindex[0]
      # Create a new row with the columns from the original DataFrame df
      new_row = pd.DataFrame(columns=process_df.columns)
      # Assign the existing values from df to the new row at the corresponding index
      new_row.loc[0, process_df.columns[:2]] = df.loc[idx_toupdate, ['URL_ID', 'URL']]
      # Update the new row with the calculated values
      for col, value in calc_values.items():
          new_row[col] = value
      # Add the new row to the process_df
      process_df = process_df._append(new_row, ignore_index=True)
      print(f"Result updated for {url_idkey}")
    else:
      print(f"!not found {url_idkey}")
    return process_df

  #process data/ processing each file
  process_df = pd.DataFrame(columns=df.columns)
  for filename in files_subset:
    filepath = os.path.join(textfile_path, filename)
    #to update values for each URL_ID
    url_idkey = re.search(r'blackassign\d{4}', filepath).group()
    if os.path.isfile(filepath):
      with open(filepath, 'r', encoding='utf-8', errors='ignore') as file:
        text = file.read()
      #tokenize text
      words = word_tokenize(text)
      sentences = sent_tokenize(text)
      totalwords = len(words)

      #calculate positive score
      positive_score = calculate_positivescore(words, positivewords)
      print(f"{filename} positive socre: {positive_score}")

      #calculate negative score
      negative_score = calculate_negativescore(words, negativewords)
      print(f"{filename} negative socre: {negative_score}")

      #calculate polarity score
      polarity_score = (positive_score - negative_score)/((positive_score+negative_score)+0.000001)
      print(f"{filename} polarity socre: {polarity_score}")

      #calculate subjective score
      subjectivity_score = (positive_score+negative_score)/((totalwords)+0.000001)
      print(f"{filename} subjectivity socre: {subjectivity_score}")

      #readibility analysis
      avg_sentencelen, percent_complexwords, fog_index = calc_readibility(words, sentences)
      print(f"{filename} avg sentencelength: {avg_sentencelen}")
      #load(df, "AVG SENTENCE LENGTH",avg_sentencelen, url_idkey)
      print(f"{filename} percentage of complex words: {percent_complexwords}")
      #load(df, "PERCENTAGE OF COMPLEX WORDS",percent_complexwords, url_idkey)
      print(f"{filename} Fog Index: {fog_index}")

      #average number of words per sentence
      avg_wordper_sentence = avg_wordspersentence(words, sentences)
      print(f"{filename} avg words per sentence: {avg_wordper_sentence}")

      #complex word count
      complexword_count = complexwords_count(words)
      print(f"{filename} complex words count: {complexword_count}")

      #word count
      cleanword_count = cleanwords_count(words, stopwords)
      print(f"{filename} clean words count: {cleanword_count}")

      #syllable count per word
      syllablecount_perword = vowel_syllable_perword(words)
      print(f"{filename} syllable count per word: {syllablecount_perword}")

      #personal pronouns
      pronouns_count = count_pronouns(text)
      print(f"{filename} personal pronouns count: {pronouns_count}")

      #avg word length
      avg_wordlength = calc_avg_wordlength(words)
      print(f"{filename} avg word length: {avg_wordlength}")
    else: print(f"df not updated for {filename}!")

    calc_values = {
      "POSITIVE SCORE": positive_score,
      "NEGATIVE SCORE": negative_score,
      "POLARITY SCORE": polarity_score,
      "SUBJECTIVITY SCORE": subjectivity_score,
      "AVG SENTENCE LENGTH": avg_sentencelen,
      "PERCENTAGE OF COMPLEX WORDS": percent_complexwords,
      "FOG INDEX": fog_index,
      "AVG NUMBER OF WORDS PER SENTENCE": avg_wordper_sentence,
      "COMPLEX WORD COUNT": complexword_count,
      "WORD COUNT": cleanword_count,
      "SYLLABLE PER WORD": syllablecount_perword,
      "PERSONAL PRONOUNS": pronouns_count,
      "AVG WORD LENGTH": avg_wordlength
    }
    try:
      process_df = appendtodf(url_idkey,calc_values, process_df)
    except Exception as e:
      print(e)
  print(process_df)
  dflist.append(process_df)  
  


#runengine(df, stopwords, files_subset, dflist)
if __name__ == '__main__':
  starttime = time.time()
  files_toprocess = os.listdir(textfile_path) 
  #files_toprocess = [r'blackassign0049.txt', r'blackassign0099.txt', r'blackassign0100.txt']
  num_processes = multiprocessing.cpu_count()
  print(str(num_processes)+ " CPUs")
  files_perprocess = len(files_toprocess) // num_processes
  print(files_perprocess)

  processes = []
  # Create a Manager object to share a list among processes
  manager = multiprocessing.Manager()
  dflist = manager.list()

  for i in range(num_processes):
    try:
      start = i*files_perprocess
      end = (i+1)*files_perprocess if i != num_processes-1 else len(files_toprocess)
      files_subset = files_toprocess[start:end]

      p = multiprocessing.Process(target=runengine, args =(df, stopwords, files_subset, dflist))
      processes.append(p)
      p.start()
    except Exception as e:
      print(e)

  print("waiting for all processes to end...")
  for i in processes:
    print(i)
  for process in processes:
    try:
      process.join()
    except Exception as e:
      print(e)
  for i in processes:
    print(i)
  
  print(str(len(dflist))+" result dataframes obtained.")
  result_df = pd.concat(dflist, ignore_index=True)
  result_df = result_df.sort_values(by='URL_ID')
  print(result_df)

  loadoutput(folderpath, result_df)
