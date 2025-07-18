from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, field_validator
import planetterp
import dotenv

dotenv.load_dotenv()

# Define structured output schema
class ProfSummary(BaseModel):
    courses: list[str]
    professor: str
    rating: float
    summary: str
    
    @field_validator('rating')
    def round_rating(cls, v):
        return round(v, 2)

class CourseSummary(BaseModel):
    course: str
    professor: str
    rating: float
    gpa: float
    summary: str
    
    @field_validator('gpa')
    def round_gpa(cls, v):
        return round(v, 2)
    
    @field_validator('rating')
    def round_rating(cls, v):
        return round(v, 2)

def format_course_for_llm(course_data: dict) -> str:
    out = f"Course: {course_data['department']}{course_data['course_number']}\n"
    out += f"Average GPA: {course_data.get('average_gpa', 'N/A')}\n"
    out += f"Credits: {course_data.get('credits', 'N/A')}\n\n"
    out += f"Professors: {', '.join(course_data.get('professors', []))}\n\n"
    out += "Top Reviews:\n"
    for review in course_data.get('reviews', [])[::-1][:10]:
        out += f"- {review['review']}\n"
    return out

# Format professor data for LLM input
def format_professor_for_llm(prof_data: dict) -> str:
    out = f"Professor: {prof_data['name']}\n"
    out += f"Department: {prof_data.get('department', 'N/A')}\n"
    out += f"Average Rating: {prof_data.get('average_rating', 'N/A')}\n"
    out += f"Courses: {', '.join(prof_data.get('courses', []))}\n\n"
    out += "Top Reviews:\n"
    for review in prof_data.get('reviews', [])[::-1][:10]:
        out += f"- {review['review']}\n"
    return out

# Set up the LLM using Groq
llm = ChatGroq(model="llama3-8b-8192")

# Define the output parser
parser = PydanticOutputParser(pydantic_object=ProfSummary)

# Create the prompt template
prompt = ChatPromptTemplate.from_messages([
    ("system", 
     """You are an assistant that summarizes university course or professor reviews.
    Your goal is to synthesize key themes in student feedback, identifying consistent patterns in teaching style, difficulty, engagement, clarity, and recurring praise or complaints.
    Avoid quoting reviews directly — instead, distill the overall sentiment and common experiences.
    Conclude with a clear recommendation: whether students should take this professor/course or consider alternatives, based on the feedback.\n
     You must respond with ONLY a valid JSON object, following this Pydantic format:\n{format_instructions}"""),
    ("human", "{info_text}")
]).partial(format_instructions=parser.get_format_instructions())

# Combine into a chain
chain = prompt | llm | parser

# Fetch PlanetTerp professor data

def generate_summary(professor_name):
    prof_data = planetterp.professor(name=professor_name, reviews=True)
    if 'error' not in prof_data:
        formatted = format_professor_for_llm(prof_data)
        result = chain.invoke({"info_text": formatted})
        return result
    else:
        return None
