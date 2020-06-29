class School:
    def __init__(self,name):
      self.name = name
      self.studentList = []

    def addStudent(self,student):
      self.studentList.append(student)

    def __str__(self):
      return "schoole name is %s" % self.name
