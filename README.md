# Document compliance agent
AI agent that parses documents and matches user input document compliance rules with values within the document

Components:
1. Document parser: Developed using Google Document AI
    -   Capable of processing documents of various file types (works best for pdf, but works with images and text files as well)
    -   Extracts headings and assigns custom processors (form, reciept, invoice, utility docs)
    -   General purpose processor in case of unknown doc type (data extraction in this case requires further processing)
    -   Dumps parsed data into json file and returns path to json file.

2. AI Agent: Built with ChatAnthropic Claude LLM
    -   Model: claude-3-5-haiku-20241022 (cost effective)
    -   First calls document parser explicitly, passes user query and documents to LLM 
    -   Ouput response wrapped into key points: rule, pass/fail status, Relevant document searched, reason for status
    -   Checks and returns pass/fail status for each rule passed.

## Requirements:
1. Google Cloud account (free trial includes $300 credit)
2. Access to ChatAnthropic models (requires credits to use) 

## To run:
1. *git clone repository*
2. Create a virtual environment and *pip install requirements.txt*
3. Create Google cloud account and start a new project
3. Create Google document AI processors (Document OCR for the initial processing, invoice, utility, receipt, form and Layout parser for unknown document type)
4. Populate the *.env* file with the following: ChatAnthropic API key, path to google cloud service account json file for the created google cloud project, project ID, location, and the processor ID for each of the created processors. 
5. The Jupyter notebook is ready to run! 


## Demonstration:
-   Documents passed: Invoice, Receipt
-   Query passed: "*Net amount in invoice equal to amount paid in receipt* and *due_date must be after or on invoice_date*"
-   Agent output:
![Screenshot 2025-05-25 222814](https://github.com/user-attachments/assets/786c4c88-7f7a-40f0-8a71-7153b514875f)


## Limitations:
-   Document parsing requires further specialized processing and requires google cloud credits.
-   This implementation requires users to create and link their own processors for document parsing
-   Document parsing is lacking when it comes to handwritten and scanned documents.
-   Logically reasoning of document type from heading requires more workshopping and refining (assumes certain keyword in the first section of the document)
-   Open source doc parsing script does not process document data properly

## Future Enhancements:
-   If doc type is identified, create new type of processor and assign to document on demand without user intervention.
-   Train custom google document AI extractor for document parsing and train with each document uploaded (implement a feedback mechanism to allow users to identify missing or incorrectly marked fields in parsed documents)
-   Allow for user creation of custom processors.
-   Possibly migrate to open source versions of document parsing to cut down on costs and allow for greater customization of document parsing 

