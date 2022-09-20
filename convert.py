import cv2

filename = './samples/3.png'
x = cv2.imread(filename)
x = cv2.cvtColor(x, cv2.COLOR_BGR2RGB)
cv2.imwrite(filename, x)
