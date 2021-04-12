from flask import render_template
from flask_wtf import FlaskForm
from werkzeug.datastructures import ImmutableMultiDict
from wikibot.wikipush import WikiPush
from wikifile.metamodel import Topic
from wtforms import BooleanField, SubmitField, Form, HiddenField, StringField,FormField
from wtforms.widgets import CheckboxInput
from wikifile.smw import SMWPart
from lodstorage.jsonable import Types, JSONAble

class Generator(object):
    '''
    SMW Page Generator Frontend
    queries the topics from the corresponding wiki
    '''


    def __init__(self, wikiId):
        '''
        Initialize generator by querying the topics and assigning forms to the topics
        Args:
            wikiId: id of the wiki
        '''
        super(Generator, self).__init__()
        self.wikiId = wikiId
        self.topics = self.getTopics(wikiId)
        self.smwParts = SMWPart.getAll(None) #ToDO: None is only for testing
        self.topicRows = {}
        self.selectionList = self.getSelectionList()




    def render(self, menuList):
        """
        Render generator as html page
        Args:
            menuList:
        Returns:
            html page of the generator
        """
        return render_template("generator.html", menuList=menuList, title="Generator", siteName=self.wikiId, dictList=self.selectionList)

    def getTopics(self, wikiId: str) -> list:
        '''

        Args:
            wikiId: id of the wiki the topic should be queried from
       Returns:
            Topics that are present at the given wiki
        '''
        # ToDo: wikiuser should be created based on the site user login info
        res = WikiPush(fromWikiId=wikiId).formatQueryResult(askQuery="{{#ask:[[isA::Topic]]|?Topic name=name|?Topic pluralName=pluralName}}")
        return [Topic(x) for x in res]

    def getSelectionList(self):
        """Assign a"""
        res = []
        for topic in self.topics:
            row = {}
            topic_name = topic.name
            tf = GenerateTopicForm(topic_name)
            row["Topic"] = tf.topic
            row["Help"] = tf.help
            row["List of"] = tf.listof
            row["Category"] = tf.category
            row["Concept"] = tf.concept
            row["Template"] = tf.template
            row["Form"] = tf.form
            row["Generate"] = tf.submit
            self.topicRows[topic_name] = {"topic":topic, "form":tf}
            res.append(row)
        return res

    def generatePages(self, topicName, requestParameter):
        '''
        Generate the selected pages for the given topicName
        Args:
            topicName: name of the topic the pages should be generated for
            requestParameter: requestParameters of the generate request
        Returns:
            Names of the pages that were generated
        '''
        print(requestParameter)
        topic = self.topicRows.get(topicName).get('topic')
        form = self.topicRows.get(topicName).get('form')
        form.validate_on_submit()
        selectedPages = self.getSelectedPages(form, requestParameter)
        # ToDo: Generate and restore generated pages
        return [x.get_page_name(topic) for x in selectedPages]

    def getSelectedPages(self, form, requestParameter):
        """Returns the SMWPart of the pages that are marked as selected in the given requestParameter"""
        res = []
        cleanList = lambda x: requestParameter.get(x) if requestParameter.get(x) is not None else []
        append = lambda part: res.append(self.smwParts.get(part))
        if 'y' in cleanList(form.help.id) :
            append("Help")
        if 'y' in cleanList(form.listof.id):
            append("List of")
        if 'y' in cleanList(form.category.id):
            append("Category")
        if 'y' in cleanList(form.concept.id):
            append("Concept")
        if 'y' in cleanList(form.template.id):
            append("Template")
        if 'y' in cleanList(form.form.id):
            append("Form")
        return res


class GenerateTopicForm(FlaskForm):
    '''Form that holds checkboxes for each SMW page that can be generated and a submit button'''
    topic = HiddenField()
    help = BooleanField()
    listof = BooleanField()
    concept = BooleanField()
    category = BooleanField()
    form = BooleanField()
    template = BooleanField()
    submit = SubmitField(label="Generate")

    def __init__(self, name):
        super().__init__()
        self.name = name
        self.topic.data=name
        self.topic.label=name
        self.updateIDs()

    def updateIDs(self):
        '''Update the id and name of each field to be unique in the context of the topics'''
        for field in ['help', 'listof', 'concept', 'category', 'template', 'form', 'submit']:
                self.__dict__[field].id = f"{field}_{self.name}"
                self.__dict__[field].name = f"{field}_{self.name}"

    @staticmethod
    def getActuatorTopic(data: ImmutableMultiDict):
        """Returns the topic name for which the submit button was submitted"""
        for d in dict(data).keys():
            if d.startswith("submit_"):
                return d.replace("submit_","")
        return None




