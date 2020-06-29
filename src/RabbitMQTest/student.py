class Student:
    def __init__(self,name,age,gender):
        self.name = name
        self.age = age
        self.gender = gender

    def updateInfo(self,name,age,gender):
        self.name = name
        self.age = age
        self.gender = gender

    def __str__(self):
        return "student name is %s, age is %d, gender is %s" % (self.name, self.age, self.gender)
