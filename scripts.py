from flask_login import current_user
from flask import flash, redirect, url_for

def check_organization_status():
    if current_user.is_organization == True:
        if current_user.answered_organization_questions == True:
            return True
        else:
            flash("You must create your organization first by answering questions about it.", "warning")
            return redirect(url_for("orginfo", user_id=current_user.id))
    else:
        flash("You are not an administrator for an organization. Please contact your organization if you think this is a mistake.", "warning")
        return redirect(url_for("home"))
    
    