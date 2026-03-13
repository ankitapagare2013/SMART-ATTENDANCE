import streamlit as st
import pandas as pd
from datetime import datetime, date

from database.db import create_tables, seed_demo_data
from auth.login import authenticate
from attendance.attendance_manager import (
    get_students,
    get_classes,
    mark_attendance,
    get_student_attendance,
    get_daily_summary,
    is_attendance_already_saved,
    add_student,
    delete_student,
    update_student,
    update_student_photo,
    get_student_by_id,
    get_student_profile_data,
)
from reports.report_generator import (
    generate_attendance_report,
    calculate_attendance_percentage,
    get_monthly_attendance_report,
    convert_df_to_csv,
    convert_df_to_excel,
)
from utils.face_utils import (
    capture_faces_for_student,
    count_face_samples,
    train_face_model,
    recognize_face_live,
)
from utils.email_utils import (
    send_monthly_reports_to_students,
    send_low_attendance_warnings,
)

EDIT_PASSWORD = "teacher123"

st.set_page_config(
    page_title="Smart Attendance System",
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_project():
    create_tables()
    seed_demo_data()

    if "user" not in st.session_state:
        st.session_state.user = None

    if "pending_recognition" not in st.session_state:
        st.session_state.pending_recognition = None

    if "edit_unlocked" not in st.session_state:
        st.session_state.edit_unlocked = False


def format_today():
    return datetime.now().strftime("%d %B %Y")


def app_header(title: str, subtitle: str):
    left, right = st.columns([4, 1])

    with left:
        st.title(title)
        st.caption(subtitle)

    with right:
        with st.container(border=True):
            st.markdown("**Today**")
            st.write(format_today())


def login_page():
    col1, col2, col3 = st.columns([1, 1.2, 1])

    with col2:
        st.title("✅ Smart Attendance System")
        st.caption("Attendance, daily and monthly reports, student management, live face recognition, and email reporting.")

        with st.container(border=True):
            st.subheader("Login Portal")

            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")

            if st.button("Login", use_container_width=True, key="login_button"):
                user = authenticate(username, password)

                if user:
                    st.session_state.user = user
                    st.success("Login successful")
                    st.rerun()
                else:
                    st.error("Invalid username or password")

        with st.expander("Demo Credentials"):
            st.write("**Admin:** admin / admin123")
            st.write("**Student:** john / john123")


def sidebar():
    user = st.session_state.user

    with st.sidebar:
        st.title("✅ Smart Attendance")
        st.caption("Attendance Management Panel")

        st.divider()

        st.markdown("### Logged In User")
        st.write(f"**Name:** {user['full_name']}")
        st.write(f"**Role:** {user['role'].title()}")
        st.write(f"**Class:** {user['class_name']}")

        st.divider()

        if st.button("Logout", use_container_width=True, key="logout_button"):
            st.session_state.user = None
            st.session_state.pending_recognition = None
            st.session_state.edit_unlocked = False
            st.rerun()


def student_management_tab():
    st.subheader("Student Management")

    with st.container(border=True):
        st.markdown("### Current Students")
        students_df = get_students("All")
        if students_df.empty:
            st.info("No students available.")
        else:
            st.dataframe(students_df, use_container_width=True, hide_index=True)

    subtab1, subtab2, subtab3 = st.tabs(["Add Student", "Edit Student", "Delete Student"])

    with subtab1:
        with st.container(border=True):
            st.markdown("### Add New Student")

            with st.form("add_student_form"):
                full_name = st.text_input("Full Name", key="add_student_full_name")
                roll_no = st.text_input("Roll Number", key="add_student_roll_no")
                class_name = st.text_input("Class Name", key="add_student_class_name")
                email = st.text_input("Email Address", key="add_student_email")
                username = st.text_input("Username", key="add_student_username")
                password = st.text_input("Password", type="password", key="add_student_password")

                submitted = st.form_submit_button("Add Student", use_container_width=True)

                if submitted:
                    if not full_name or not roll_no or not class_name or not username or not password:
                        st.error("Please fill all required fields.")
                    else:
                        success, message = add_student(
                            full_name=full_name,
                            username=username,
                            password=password,
                            class_name=class_name,
                            email=email,
                            roll_no=roll_no,
                        )
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)

    with subtab2:
        with st.container(border=True):
            st.markdown("### Edit Student")
            search_text = st.text_input(
                "Search Student",
                placeholder="Name, roll no, username, email",
                key="edit_student_search"
            )
            filtered_df = get_students("All", search_text)

            if filtered_df.empty:
                st.info("No student found.")
            else:
                student_options = {
                    f"{row['full_name']} | {row['roll_no']} | {row['class_name']} | ID {row['id']}": int(row["id"])
                    for _, row in filtered_df.iterrows()
                }

                selected_label = st.selectbox(
                    "Select Student",
                    list(student_options.keys()),
                    key="edit_student_selectbox"
                )
                selected_student_id = student_options[selected_label]
                selected_row = filtered_df[filtered_df["id"] == selected_student_id].iloc[0]

                with st.form("edit_student_form"):
                    full_name = st.text_input("Full Name", value=selected_row["full_name"], key="edit_student_full_name")
                    roll_no = st.text_input("Roll Number", value=selected_row["roll_no"], key="edit_student_roll_no")
                    class_name = st.text_input("Class Name", value=selected_row["class_name"], key="edit_student_class_name")
                    email = st.text_input("Email Address", value=selected_row["email"], key="edit_student_email")
                    username = st.text_input("Username", value=selected_row["username"], key="edit_student_username")

                    submitted = st.form_submit_button("Update Student", use_container_width=True)

                    if submitted:
                        success, message = update_student(
                            selected_student_id,
                            full_name,
                            username,
                            class_name,
                            email,
                            roll_no,
                        )
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)

    with subtab3:
        with st.container(border=True):
            st.markdown("### Delete Student")
            search_text = st.text_input(
                "Search Student to Delete",
                placeholder="Name, roll no, username, email",
                key="delete_student_search"
            )
            filtered_df = get_students("All", search_text)

            if filtered_df.empty:
                st.info("No student found.")
            else:
                student_options = {
                    f"{row['full_name']} | {row['roll_no']} | {row['class_name']} | ID {row['id']}": int(row["id"])
                    for _, row in filtered_df.iterrows()
                }

                selected_label = st.selectbox(
                    "Select Student to Delete",
                    list(student_options.keys()),
                    key="delete_student_selectbox"
                )
                selected_student_id = student_options[selected_label]

                if st.button("Delete Selected Student", use_container_width=True, key="delete_student_button"):
                    success, message = delete_student(selected_student_id)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)


def face_registration_tab():
    st.subheader("Face Registration")

    students_df = get_students("All")

    if students_df.empty:
        st.warning("No students available.")
        return

    student_options = {
        f"{row['full_name']} | {row['roll_no']} | {row['class_name']} | ID {row['id']}": int(row["id"])
        for _, row in students_df.iterrows()
    }

    selected_student_label = st.selectbox(
        "Select Student",
        list(student_options.keys()),
        key="face_registration_student_selectbox"
    )
    selected_student_id = student_options[selected_student_label]

    st.info(f"Current saved samples: {count_face_samples(selected_student_id)}")
    save_count = st.slider(
        "Number of samples to capture",
        3,
        10,
        5,
        key="face_registration_sample_slider"
    )

    st.write("When the camera opens:")
    st.write("Press **S** to save one face sample.")
    st.write("Press **Q** to stop.")

    if st.button("Start Live Face Registration", use_container_width=True, key="start_face_registration_button"):
        success, message, reference_path = capture_faces_for_student(selected_student_id, save_count)

        if success:
            if reference_path:
                update_student_photo(selected_student_id, reference_path)
            st.success(message)
            st.info(f"Total samples now: {count_face_samples(selected_student_id)}")
        else:
            st.error(message)

    if st.button("Train Face Model", use_container_width=True, key="train_face_model_button"):
        success, student_count = train_face_model()
        if success:
            st.success(f"Face model trained successfully for {student_count} student(s).")
        else:
            st.error("No face samples found. Register student faces first.")


def face_recognition_tab():
    st.subheader("Face Recognition Attendance")

    recognition_date = st.date_input(
        "Attendance Date for Face Recognition",
        value=date.today(),
        max_value=date.today(),
        key="face_attendance_date"
    )
    recognition_date_str = recognition_date.isoformat()

    st.write("When the camera opens:")
    st.write("Press **S** to capture the current face.")
    st.write("Press **Q** to cancel.")

    if st.button("Start Live Face Recognition", use_container_width=True, key="start_face_recognition_button"):
        student_id, confidence, captured_path, message = recognize_face_live()

        if student_id is None:
            st.session_state.pending_recognition = {
                "status": "not_found",
                "student": None,
                "confidence": confidence,
                "captured_path": captured_path,
                "message": message,
                "recognition_date": recognition_date_str,
            }
        else:
            student = get_student_by_id(student_id)
            st.session_state.pending_recognition = {
                "status": "found",
                "student": student,
                "confidence": confidence,
                "captured_path": captured_path,
                "message": message,
                "recognition_date": recognition_date_str,
            }

        st.rerun()

    pending = st.session_state.pending_recognition

    if pending:
        st.markdown("---")

        if pending["status"] == "found" and pending["student"]:
            student = pending["student"]

            st.success("Student matched. Verify details before marking attendance.")

            c1, c2 = st.columns(2)

            with c1:
                st.markdown("### Captured Attendance Photo")
                if pending["captured_path"]:
                    st.image(pending["captured_path"], width=320)

            with c2:
                st.markdown("### Matched Student Information")
                st.write(f"**Name:** {student['full_name']}")
                st.write(f"**Roll No:** {student['roll_no']}")
                st.write(f"**Class:** {student['class_name']}")
                st.write(f"**Username:** {student['username']}")
                st.write(f"**Confidence:** {round(pending['confidence'], 2)}")
                if student["photo_path"]:
                    st.image(student["photo_path"], caption="Registered Reference Photo", width=320)
                else:
                    st.warning("Reference photo not available.")

            b1, b2 = st.columns(2)

            with b1:
                if st.button("Mark Attendance", use_container_width=True, key="mark_face_attendance_button"):
                    mark_attendance(
                        student["id"],
                        "Present",
                        "Face Recognition",
                        pending["recognition_date"],
                    )
                    st.session_state.pending_recognition = None
                    st.success(f"Attendance marked Present for {student['full_name']}.")
                    st.rerun()

            with b2:
                if st.button("Reject", use_container_width=True, key="reject_face_match_button"):
                    st.session_state.pending_recognition = {
                        "status": "rejected",
                        "student": None,
                        "confidence": pending["confidence"],
                        "captured_path": pending["captured_path"],
                        "message": "Teacher rejected the match.",
                        "recognition_date": pending["recognition_date"],
                    }
                    st.rerun()

        else:
            st.error("Record not found.")

            if pending["captured_path"]:
                st.image(pending["captured_path"], caption="Captured Photo", width=320)

            st.write(f"**Reason:** {pending['message']}")
            if pending["confidence"] is not None:
                st.write(f"**Confidence:** {round(pending['confidence'], 2)}")

            if st.button("Clear Result", use_container_width=True, key="clear_face_result_button"):
                st.session_state.pending_recognition = None
                st.rerun()


def daily_report_tab(selected_class, selected_date, search_text):
    st.subheader("Daily Report")

    selected_date_str = selected_date.isoformat()
    daily_summary = get_daily_summary(selected_class, selected_date_str)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Students", daily_summary["total_students"])
    m2.metric("Present", daily_summary["present"])
    m3.metric("Absent", daily_summary["absent"])
    m4.metric("Late", daily_summary["late"])
    m5.metric("Unmarked", daily_summary["unmarked"])

    report_df = generate_attendance_report(selected_class, selected_date_str)

    if search_text.strip() and not report_df.empty:
        search_value = search_text.strip().lower()
        report_df = report_df[
            report_df["full_name"].str.lower().str.contains(search_value, na=False) |
            report_df["roll_no"].str.lower().str.contains(search_value, na=False) |
            report_df["username"].str.lower().str.contains(search_value, na=False) |
            report_df["email"].str.lower().str.contains(search_value, na=False)
        ]

    if report_df.empty:
        st.info("No daily report data available.")
    else:
        report_df["status"] = report_df["status"].fillna("Unmarked")

        with st.container(border=True):
            st.markdown(f"### Attendance Table for {selected_date.strftime('%d %B %Y')}")
            st.dataframe(report_df, use_container_width=True, hide_index=True)

        d1, d2 = st.columns(2)

        with d1:
            csv_data = convert_df_to_csv(report_df)
            st.download_button(
                label="Download Daily Report CSV",
                data=csv_data,
                file_name=f"attendance_report_{selected_date_str}.csv",
                mime="text/csv",
                use_container_width=True,
                key="download_daily_csv"
            )

        with d2:
            excel_data = convert_df_to_excel(report_df)
            st.download_button(
                label="Download Daily Report Excel",
                data=excel_data,
                file_name=f"attendance_report_{selected_date_str}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="download_daily_excel"
            )

    st.write("")
    already_saved = is_attendance_already_saved(selected_class, selected_date_str)

    if already_saved:
        st.warning("Attendance for this date is already saved. Use Edit Attendance to make changes.")
        return

    with st.container(border=True):
        st.markdown(f"### Mark Attendance for {selected_date.strftime('%d %B %Y')}")

        students_df = get_students(selected_class, search_text)

        if students_df.empty:
            st.info("No students found for the selected class or search filter.")
            return

        with st.form("attendance_form"):
            status_map = {}

            header_cols = st.columns([3, 2, 2, 2])
            header_cols[0].markdown("**Student Name**")
            header_cols[1].markdown("**Roll No**")
            header_cols[2].markdown("**Class**")
            header_cols[3].markdown("**Status**")

            st.divider()

            for _, row in students_df.iterrows():
                cols = st.columns([3, 2, 2, 2])
                cols[0].write(row["full_name"])
                cols[1].write(row["roll_no"])
                cols[2].write(row["class_name"])
                status_map[row["id"]] = cols[3].selectbox(
                    f"status_{row['id']}",
                    ["Present", "Absent", "Late"],
                    label_visibility="collapsed",
                    key=f"daily_mark_status_{row['id']}"
                )

            submitted = st.form_submit_button(
                f"Save Attendance for {selected_date.strftime('%d %B %Y')}",
                use_container_width=True
            )

            if submitted:
                for _, row in students_df.iterrows():
                    mark_attendance(
                        int(row["id"]),
                        status_map[row["id"]],
                        st.session_state.user["username"],
                        selected_date_str,
                    )

                st.success("Attendance saved successfully.")
                st.rerun()


def monthly_report_tab(selected_class):
    st.subheader("Monthly Report")

    current_year = datetime.now().year
    years = list(range(current_year - 2, current_year + 1))

    c1, c2 = st.columns(2)

    with c1:
        selected_year = st.selectbox(
            "Select Year",
            years,
            index=len(years) - 1,
            key="monthly_report_year"
        )

    with c2:
        selected_month = st.selectbox(
            "Select Month",
            list(range(1, 13)),
            index=datetime.now().month - 1,
            format_func=lambda x: datetime(2000, x, 1).strftime("%B"),
            key="monthly_report_month"
        )

    monthly_df = get_monthly_attendance_report(selected_class, selected_year, selected_month)

    if monthly_df.empty:
        st.info("No monthly attendance data available.")
        return

    with st.container(border=True):
        st.markdown("### Monthly Attendance Table")
        st.dataframe(monthly_df, use_container_width=True, hide_index=True)

    ch1, ch2 = st.columns(2)

    with ch1:
        with st.container(border=True):
            st.markdown("### Monthly Attendance Percentage")
            st.bar_chart(
                monthly_df.set_index("full_name")["monthly_attendance_percentage"]
            )

    with ch2:
        with st.container(border=True):
            st.markdown("### Monthly Status Totals")
            totals_df = pd.DataFrame({
                "Status": ["Present", "Absent", "Late"],
                "Count": [
                    int(monthly_df["present_days"].sum()),
                    int(monthly_df["absent_days"].sum()),
                    int(monthly_df["late_days"].sum()),
                ],
            }).set_index("Status")
            st.bar_chart(totals_df)

    d1, d2 = st.columns(2)

    with d1:
        csv_data = convert_df_to_csv(monthly_df)
        st.download_button(
            label="Download Monthly Report CSV",
            data=csv_data,
            file_name=f"monthly_attendance_{selected_year}_{selected_month:02d}.csv",
            mime="text/csv",
            use_container_width=True,
            key="download_monthly_csv"
        )

    with d2:
        excel_data = convert_df_to_excel(monthly_df)
        st.download_button(
            label="Download Monthly Report Excel",
            data=excel_data,
            file_name=f"monthly_attendance_{selected_year}_{selected_month:02d}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="download_monthly_excel"
        )

    st.write("")

    if st.button("Send Monthly Reports", use_container_width=True, key="send_monthly_reports_button"):
        try:
            sender_email = st.secrets["EMAIL_SENDER"]
            app_password = st.secrets["EMAIL_APP_PASSWORD"]

            sent, failed = send_monthly_reports_to_students(
                sender_email=sender_email,
                app_password=app_password,
                monthly_df=monthly_df,
                year=selected_year,
                month=selected_month,
            )

            if sent > 0:
                st.success(f"Monthly reports sent successfully to {sent} student(s).")

            if failed:
                st.warning("Some emails failed:")
                for item in failed:
                    st.write(f"- {item}")

        except Exception as e:
            st.error(f"Mail sending failed: {e}")


def student_profile_tab(selected_class):
    st.subheader("Student Profile")

    search_text = st.text_input(
        "Search Student Profile",
        placeholder="Search by name, roll no, username, or email",
        key="profile_search"
    )

    students_df = get_students(selected_class, search_text)

    if students_df.empty:
        st.info("No student found.")
        return

    student_options = {
        f"{row['full_name']} | {row['roll_no']} | {row['class_name']} | ID {row['id']}": int(row["id"])
        for _, row in students_df.iterrows()
    }

    selected_student_label = st.selectbox(
        "Select Student",
        list(student_options.keys()),
        key="student_profile_selectbox"
    )

    selected_student_id = student_options[selected_student_label]

    profile, attendance_df, summary = get_student_profile_data(selected_student_id)

    if profile is None:
        st.error("Student profile not found.")
        return

    top1, top2, top3, top4 = st.columns(4)
    top1.metric("Attendance %", f"{summary['attendance_percentage']}%")
    top2.metric("Present Days", summary["present_days"])
    top3.metric("Absent Days", summary["absent_days"])
    top4.metric("Late Days", summary["late_days"])

    c1, c2 = st.columns([1, 2])

    with c1:
        with st.container(border=True):
            st.markdown("### Student Information")
            st.write(f"**Name:** {profile['full_name']}")
            st.write(f"**Roll No:** {profile['roll_no']}")
            st.write(f"**Class:** {profile['class_name']}")
            st.write(f"**Username:** {profile['username']}")
            st.write(f"**Email:** {profile['email']}")
            if profile.get("photo_path"):
                st.image(profile["photo_path"], caption="Student Photo", use_container_width=True)

    with c2:
        with st.container(border=True):
            st.markdown("### Attendance History")
            if attendance_df.empty:
                st.info("No attendance history found.")
            else:
                st.dataframe(attendance_df, use_container_width=True, hide_index=True)


def edit_attendance_tab(selected_class):
    st.subheader("Edit Attendance")

    if not st.session_state.edit_unlocked:
        with st.container(border=True):
            st.markdown("### Enter Edit Password")
            edit_password = st.text_input("Password", type="password", key="edit_password_input")
            if st.button("Unlock Edit Attendance", use_container_width=True, key="unlock_edit_button"):
                if edit_password == EDIT_PASSWORD:
                    st.session_state.edit_unlocked = True
                    st.success("Edit attendance unlocked.")
                    st.rerun()
                else:
                    st.error("Incorrect password.")
        return

    if st.button("Lock Edit Attendance", use_container_width=True, key="lock_edit_button"):
        st.session_state.edit_unlocked = False
        st.rerun()

    edit_date = st.date_input(
        "Select Date to Edit Attendance",
        value=date.today(),
        max_value=date.today(),
        key="edit_attendance_date"
    )
    edit_date_str = edit_date.isoformat()

    search_text = st.text_input(
        "Search Student in Edit Attendance",
        placeholder="Search by name or roll no",
        key="edit_attendance_search"
    )

    students_df = get_students(selected_class, search_text)
    daily_df = generate_attendance_report(selected_class, edit_date_str)

    if search_text.strip() and not daily_df.empty:
        search_value = search_text.strip().lower()
        daily_df = daily_df[
            daily_df["full_name"].str.lower().str.contains(search_value, na=False) |
            daily_df["roll_no"].str.lower().str.contains(search_value, na=False)
        ]

    if students_df.empty:
        st.info("No students found for the selected class or search.")
        return

    existing_status_map = {}
    if not daily_df.empty:
        for _, row in daily_df.iterrows():
            if pd.notna(row["status"]):
                existing_status_map[row["id"]] = row["status"]

    with st.container(border=True):
        st.markdown(f"### Edit Attendance for {edit_date.strftime('%d %B %Y')}")

        with st.form("edit_attendance_form"):
            status_map = {}

            header_cols = st.columns([3, 2, 2, 2])
            header_cols[0].markdown("**Student Name**")
            header_cols[1].markdown("**Roll No**")
            header_cols[2].markdown("**Class**")
            header_cols[3].markdown("**Status**")

            st.divider()

            for _, row in students_df.iterrows():
                default_status = existing_status_map.get(row["id"], "Present")
                status_options = ["Present", "Absent", "Late"]
                default_index = status_options.index(default_status)

                cols = st.columns([3, 2, 2, 2])
                cols[0].write(row["full_name"])
                cols[1].write(row["roll_no"])
                cols[2].write(row["class_name"])
                status_map[row["id"]] = cols[3].selectbox(
                    f"edit_status_{row['id']}",
                    status_options,
                    index=default_index,
                    label_visibility="collapsed",
                    key=f"edit_attendance_status_{row['id']}"
                )

            submitted = st.form_submit_button(
                f"Update Attendance for {edit_date.strftime('%d %B %Y')}",
                use_container_width=True
            )

            if submitted:
                for _, row in students_df.iterrows():
                    mark_attendance(
                        int(row["id"]),
                        status_map[row["id"]],
                        st.session_state.user["username"],
                        edit_date_str,
                    )
                st.success("Attendance updated successfully.")
                st.rerun()


def low_attendance_panel_tab(selected_class):
    st.subheader("Low Attendance Panel")

    percentage_df = calculate_attendance_percentage()

    if selected_class != "All" and not percentage_df.empty:
        percentage_df = percentage_df[percentage_df["class_name"] == selected_class]

    if percentage_df.empty:
        st.info("No attendance data available.")
        return

    low_df = percentage_df[percentage_df["attendance_percentage"] < 75].copy()
    low_df = low_df.sort_values(by="attendance_percentage")

    if low_df.empty:
        st.success("No students are below the 75% attendance threshold.")
        return

    st.error(f"{len(low_df)} student(s) are below 75% attendance.")

    c1, c2, c3 = st.columns(3)
    c1.metric("Below 75%", len(low_df))
    c2.metric("Lowest Attendance", f"{float(low_df['attendance_percentage'].min()):.2f}%")
    c3.metric("Average of Low Group", f"{float(low_df['attendance_percentage'].mean()):.2f}%")

    with st.container(border=True):
        st.markdown("### Low Attendance Students")
        st.dataframe(
            low_df[
                [
                    "roll_no",
                    "full_name",
                    "class_name",
                    "email",
                    "present_days",
                    "absent_days",
                    "late_days",
                    "attendance_percentage",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

    with st.container(border=True):
        st.markdown("### Low Attendance Chart")
        st.bar_chart(low_df.set_index("full_name")["attendance_percentage"])

    d1, d2 = st.columns(2)

    with d1:
        csv_data = convert_df_to_csv(low_df)
        st.download_button(
            label="Download Low Attendance CSV",
            data=csv_data,
            file_name="low_attendance_students.csv",
            mime="text/csv",
            use_container_width=True,
            key="download_low_attendance_csv"
        )

    with d2:
        excel_data = convert_df_to_excel(low_df)
        st.download_button(
            label="Download Low Attendance Excel",
            data=excel_data,
            file_name="low_attendance_students.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="download_low_attendance_excel"
        )

    st.write("")

    if st.button("Send Defaulter Warning Emails", use_container_width=True, key="send_low_attendance_warning_button"):
        try:
            sender_email = st.secrets["EMAIL_SENDER"]
            app_password = st.secrets["EMAIL_APP_PASSWORD"]

            sent, failed = send_low_attendance_warnings(
                sender_email=sender_email,
                app_password=app_password,
                low_df=low_df,
            )

            if sent > 0:
                st.success(f"Warning emails sent successfully to {sent} student(s).")

            if failed:
                st.warning("Some emails failed:")
                for item in failed:
                    st.write(f"- {item}")

        except Exception as e:
            st.error(f"Mail sending failed: {e}")


def admin_dashboard():
    app_header(
        "Admin Dashboard",
        "Daily and monthly attendance, student management, face recognition, protected editing, and low attendance tracking."
    )

    with st.container(border=True):
        c1, c2, c3 = st.columns(3)

        with c1:
            classes = ["All"] + get_classes()
            selected_class = st.selectbox("Select Class", classes, key="admin_selected_class")

        with c2:
            selected_date = st.date_input(
                "Select Attendance Date",
                value=date.today(),
                max_value=date.today(),
                key="admin_selected_date"
            )

        with c3:
            search_text = st.text_input(
                "Search Students",
                placeholder="Name, roll no, username, email",
                key="admin_search_students"
            )

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "Daily Report",
        "Monthly Report",
        "Low Attendance Panel",
        "Student Management",
        "Face Registration",
        "Face Recognition",
        "Edit Attendance",
    ])

    with tab1:
        daily_report_tab(selected_class, selected_date, search_text)

    with tab2:
        monthly_report_tab(selected_class)

    with tab3:
        low_attendance_panel_tab(selected_class)

    with tab4:
        student_management_tab()
        st.write("")
        student_profile_tab(selected_class)

    with tab5:
        face_registration_tab()

    with tab6:
        face_recognition_tab()

    with tab7:
        edit_attendance_tab(selected_class)


def student_dashboard():
    user = st.session_state.user

    app_header(
        "Student Dashboard",
        "View your attendance history and monitor your attendance percentage."
    )

    attendance_df = get_student_attendance(user["id"])
    percentage_df = calculate_attendance_percentage()
    student_percentage = percentage_df[
        percentage_df["username"] == user["username"]
    ]

    c1, c2, c3 = st.columns(3)

    if student_percentage.empty:
        c1.metric("Attendance Percentage", "0%")
        c2.metric("Present Days", "0")
        c3.metric("Total Days", "0")
    else:
        row = student_percentage.iloc[0]
        c1.metric("Attendance Percentage", f"{float(row['attendance_percentage'])}%")
        c2.metric("Present Days", int(row["present_days"]))
        c3.metric("Total Days", int(row["total_days"]))

    if not student_percentage.empty:
        percent = float(student_percentage.iloc[0]["attendance_percentage"])
        if percent < 75:
            st.error("Your attendance is below 75%. Please improve your attendance.")
        else:
            st.success("Your attendance is in a safe range.")

    col1, col2 = st.columns([1.5, 1])

    with col1:
        with st.container(border=True):
            st.subheader("My Attendance History")

            if attendance_df.empty:
                st.info("No attendance record found.")
            else:
                st.dataframe(attendance_df, use_container_width=True, hide_index=True)

    with col2:
        with st.container(border=True):
            st.subheader("My Attendance Summary")

            if student_percentage.empty:
                st.info("No percentage data available.")
            else:
                st.dataframe(
                    student_percentage[
                        ["roll_no", "full_name", "present_days", "absent_days", "late_days", "attendance_percentage"]
                    ],
                    use_container_width=True,
                    hide_index=True,
                )


def main():
    init_project()

    if not st.session_state.user:
        login_page()
        return

    sidebar()

    if st.session_state.user["role"] == "admin":
        admin_dashboard()
    else:
        student_dashboard()


if __name__ == "__main__":
    main()