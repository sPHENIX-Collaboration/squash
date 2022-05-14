import sqlite3

db = str(input('Enter the filename of the database from which you wish to remove: '))


conn = sqlite3.connect(db)
c = conn.cursor()
entry0 = 0
entry1 = 1
while(entry0 != entry1):
    entry0 = str(input('Enter the serial number to delete: '))
    entry1 = str(input('Re-enter the serial number to delete: '))
    if(entry0 != entry1):
        print('Serial numbers not the same. Try again.')

print('Are you sure you want to delete ' + entry0 + '?')
entry2 = str(input('Enter yes to continue, or anything else to cancel: '))
if(entry2.lower() != 'yes'):
    print('Cancelling and terminating.')
    quit()

deletion = c.execute("DELETE FROM data WHERE Serial=?", (entry0,))
conn.commit()
c.close
