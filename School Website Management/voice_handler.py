from langchain.agents import AgentExecutor
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
import os
import dotenv


# fetch the api from the .env variable
dotenv.load_dotenv()
openai_api_key = os.environ.get("OPENAI_API_KEY")

# Initialize LLM
llm = ChatOpenAI(model="gpt-4", api_key=openai_api_key)

from langchain_core.prompts import PromptTemplate
prompt = PromptTemplate.from_template('''You are an intelligent assistant designed to respond or guide and redirect users on a school website to available routes. The available routes are:
                                      [/dashboard, /score-entry, /student-report, /class-report, /admin-dashboard, /contact, /help, /update-profile, /logout].
                                      How ever there are roles on the website, therefore certain privileges and certain restrictions apply to each role.

                                    1. **Student**:
                                    - "/dashboard": For general navigation or dashboard access.
                                    - "/student-report": For viewing student performance details.
                                    - General routes: "/contact", "/help", "/update-profile", "/logout".

                                    2. **Staff**:
                                    - "/dashboard": For general navigation or dashboard access.
                                    - "/class-report": For managing or viewing class performance.
                                    - "/score-entry": For entering student scores.
                                    - General routes: "/contact", "/help", "/update-profile", "/logout".

                                    3. **Admin**:
                                    - "/dashboard": For general navigation or dashboard access.
                                    - "/class-report": For managing or viewing class performance.
                                    - "/score-entry": For entering student scores.
                                    - "/admin-dashboard": For administrative tasks.
                                    - General routes: "/contact", "/help", "/update-profile", "/logout".

                                      
                                    Your task:
                                    1. Understand the user's role and the corresponding route restrictions.
                                    2. If the user requests an unavailable route based on their role, respond with: "You do not have access to this route."
                                    3. If the user just wants to discuss, respond appropriately based on the context. Otherwise, match the request to a route within their role-specific access.
                                    4. If the request is unclassifiable, default to the "home" route: "/dashboard".
                                    5. If it is a route request, Always output only the route as plain text and nothing else.
                                    NOTE: YOUR ROUTE OUTPUT WILL BE PASSED INTO A REDIRECT FUNCTION. MAKE SURE IT IS A VALID ROUTE AND NO ADDITIONAL CONTENT SHOULD BE IN THE OUTPUT

                                    Other Route Definitions:
                                    - "/contact": For inquiries about reaching the school or contacting support.
                                    - "/help": For guidance, FAQs, or problem-solving.
                                    - "/update-profile": This is for updating user account details or profile information.
                                    - "/logout": To log out of the website securely.


                                    Key Points:
                                    - Match the user's intent based on keywords or phrasing.
                                    - Be flexible with synonyms or alternative ways users might phrase requests.
                                    - Example Requests:
                                    - "Take me to the report page" → `/student-report`
                                    - "How do I contact the school?" → `/contact`
                                    - "I need assistance" → `/help`
                                    - "What's this site about?" → `/dashboard`
                                            

                                    Input:
                                    - User Role: {role}
                                    - User Request: {input}

                                    Your output:
                                    - A valid route or an appropriate response.'''
                                    )       

chain = prompt | llm


# ROUTE_SCHEMA = [
#     "/dashboard, "/score-entry, /student-report, /class-report, /admin-dashboard, /contact, /help", /update-profile, /logout"
#     "/submit-scores", "/set-term", "/score-entry/reset-filters", "/score-entry/submit-scores",
#     "/admin-dashboard/set-term", "/admin-dashboard/add-staff", "/admin-dashboard/manage-staff/fetch-assignments",
#     "/admin-dashboard/manage-staff/delete-class", "/admin-dashboard/manage-staff/delete-subjects",
#     "/admin-dashboard/manage-staff/delete-staff", "/admin-dashboard/manage-staff/add-classes-subjects",
#     "/admin-dashboard/manage-staff/toggle-admin", "/admin-dashboard/generate-codes/generate-student-codes",
#     "/admin-dashboard/generate-codes/download-student-codes", "/admin-dashboard/generate-codes/generate-staff-codes",
#     "/admin-dashboard/generate-codes/download-staff-codes"
# ]

# Define valid routes for each role
ROUTE_ACCESS = {
    "student": ["/dashboard", "/student-report", "/contact", "/help", "/update-profile", "/logout"],
    "staff": ["/dashboard", "/class-report", "/score-entry", "/contact", "/help", "/update-profile", "/logout"],
    "admin": ["/dashboard", "/class-report", "/score-entry", "/admin-dashboard", "/contact", "/help", "/update-profile", "/logout"],
}

        
def process_voice_command(user_input, user_role):
    """Process user input from the voice assistant using LLM, considering role-based access."""
    try:
        print(f"Processing voice user_input: {user_input} | Role: {user_role}")
            
        # Use the LLM to process the input
        result = chain.invoke({"input": user_input, "role": user_role})
        print(f'\nLLM Output: {result}')  # Debugging point

        route = result.content.strip()
        print("\nMatched Route:", route)  # Debugging point

        # List of valid routes
        valid_routes = ROUTE_ACCESS.get(user_role, [])
        print("\nValid Routes:", valid_routes)  # Debugging point

        # List of valid routes
        if route in valid_routes:
            return {"redirect": route, "message": f"Redirecting to {route}."}
        
        elif route.startswith("/"):
            return {"message": "You do not have access to this route."}
        
        # If the result is not a route, treat it as a general message
        return {"message": route}

    except Exception as e:
        return {"message": f"An error occurred: {str(e)}"}, 500
