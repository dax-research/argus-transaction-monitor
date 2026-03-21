import pandas as pd
df = pd.read_csv('../Fraud_dataset.csv')
cols = list(df.columns)
print('ALL COLUMNS:', cols)
print('Fraud_Label values:', df['Fraud_Label'].value_counts().to_dict())
checks = ['Daily_Transaction_Count','Avg_Transaction_Amount_7d','Failed_Transaction_Count_7d',
          'New_Device','Is_Weekend','Account_Balance','Device_Type','Transaction_Amount']
for c in checks:
    print(f'  Has {c}:', c in cols)
