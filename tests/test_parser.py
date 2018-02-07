import unittest

from text2jira import parse_lines


class TestParseIssues(unittest.TestCase):
    def test_multi_comments(self):
        input = """
- Performance Improvements (X)
    * we're doing performance improvements on the CPU only
    * moving to GPU is not an option right now
    * main strategy is to cache long running tasks to re-use them    
        + Cache Strategy A
            * generate the road			
            * part of this task is to come up with an LRU (or similar)
        + Cache Strategy B			
            * cache and re-use the RGBA Bitmaps
        + Profile Texture Synthesis
            * Pair programming 
            * afterwards discuss further steps
            * part of this task is to come up with an LRU		    
        + [Optional] Run synthesis non blocking
            * Idea is to move the actual synthesis out of the Read method
            * Needs some sort of queuing mechanism 
            * One thread then more or less continuously works
            * Needs discussion
"""
        issues = parse_lines(input.split("\n"))
        self.assertEquals(len(issues), 1)
        description = issues[0]["description"].split("\n")[:-1]
        self.assertEquals(len(description), 3)

        sub_issues = issues[0]["sub_issues"]
        self.assertEquals(len(sub_issues),4)

        description = sub_issues[0]["description"].split("\n")[:-1]
        self.assertEquals(len(description), 2)

        description = sub_issues[1]["description"].split("\n")[:-1]
        self.assertEquals(len(description), 1)

        description = sub_issues[2]["description"].split("\n")[:-1]
        self.assertEquals(len(description), 3)

        description = sub_issues[3]["description"].split("\n")[:-1]
        self.assertEquals(len(description), 4)

    def test_assignee(self):
        input = """
- Performance Improvements (X) [userA]
    + Cache Road
    + Cache Textures [userB]			
- Profile Textures
"""
        issues = parse_lines(input.split("\n"))
        self.assertEquals(len(issues), 2)
        assignee = issues[0]["assignee"]
        self.assertEquals(assignee, "userA")
        summary =  issues[0]["summary"]
        self.assertEquals(summary, "Performance Improvements")

        sub_issues = issues[0]["sub_issues"]
        self.assertEquals(len(sub_issues),2)

        assignee = sub_issues[0]["assignee"]
        self.assertEquals(assignee, None)

        assignee = sub_issues[1]["assignee"]
        self.assertEquals(assignee, "userB")
        summary =  sub_issues[1]["summary"]
        self.assertEquals(summary, "Cache Textures")

        assignee = issues[1]["assignee"]
        self.assertEquals(assignee, None)


