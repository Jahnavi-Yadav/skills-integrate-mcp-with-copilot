document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const roleSelect = document.getElementById("role");
  const signupForm = document.getElementById("signup-form");
  const uploadForm = document.getElementById("upload-form");
  const uploadActivitySelect = document.getElementById("upload-activity");
  const attendanceFileInput = document.getElementById("attendance-file");
  const messageDiv = document.getElementById("message");

  function showMessage(text, type = "info") {
    messageDiv.textContent = text;
    messageDiv.className = type;
    messageDiv.classList.remove("hidden");
    clearTimeout(showMessage.timeout);
    showMessage.timeout = setTimeout(() => {
      messageDiv.classList.add("hidden");
    }, 5000);
  }

  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      const activities = await response.json();

      activitiesList.innerHTML = "";
      activitySelect.innerHTML = "<option value=''>-- Select an activity --</option>";
      uploadActivitySelect.innerHTML = "<option value=''>-- Select an activity --</option>";

      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft = details.max_participants - details.participants.length;

        const participantsHTML =
          details.participants.length > 0
            ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${details.participants
                  .map((participant) => {
                    const email = participant.email;
                    const role = participant.role || "participant";
                    return `<li>
                      <span class="participant-email">${email}</span>
                      <span class="participant-role">${role}</span>
                      <select class="role-select" data-activity="${name}" data-email="${email}">
                        <option value="participant" ${role === "participant" ? "selected" : ""}>participant</option>
                        <option value="organizer" ${role === "organizer" ? "selected" : ""}>organizer</option>
                        <option value="volunteer" ${role === "volunteer" ? "selected" : ""}>volunteer</option>
                      </select>
                      <button class="update-role-btn" data-activity="${name}" data-email="${email}">Update</button>
                      <button class="delete-btn" data-activity="${name}" data-email="${email}">❌</button>
                    </li>`;
                  })
                  .join("")}
              </ul>
            </div>`
            : `<p><em>No participants yet</em></p>`;

        activityCard.innerHTML = `
          <h4>${name}</h4>
          <p>${details.description}</p>
          <p><strong>Schedule:</strong> ${details.schedule}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants-container">
            ${participantsHTML}
          </div>
        `;

        activitiesList.appendChild(activityCard);

        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);

        const uploadOption = option.cloneNode(true);
        uploadActivitySelect.appendChild(uploadOption);
      });

      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });

      document.querySelectorAll(".update-role-btn").forEach((button) => {
        button.addEventListener("click", handleRoleUpdate);
      });
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  async function handleUnregister(event) {
    const button = event.target;
    const activity = button.getAttribute("data-activity");
    const email = button.getAttribute("data-email");

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/unregister?email=${encodeURIComponent(email)}`,
        {
          method: "DELETE",
        }
      );

      const result = await response.json();
      if (response.ok) {
        showMessage(result.message, "success");
        fetchActivities();
      } else {
        showMessage(result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage("Failed to unregister. Please try again.", "error");
      console.error("Error unregistering:", error);
    }
  }

  async function handleRoleUpdate(event) {
    const button = event.target;
    const activity = button.getAttribute("data-activity");
    const email = button.getAttribute("data-email");
    const row = button.closest("li");
    const roleSelect = row.querySelector(".role-select");
    const role = roleSelect ? roleSelect.value : "participant";

    try {
      const formData = new FormData();
      formData.append("role", role);
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/attendance/${encodeURIComponent(email)}`,
        {
          method: "PUT",
          body: formData,
        }
      );

      const result = await response.json();
      if (response.ok) {
        showMessage(result.message, "success");
        fetchActivities();
      } else {
        showMessage(result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage("Failed to update role. Please try again.", "error");
      console.error("Error updating role:", error);
    }
  }

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const activity = activitySelect.value;
    const role = roleSelect.value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/signup?email=${encodeURIComponent(email)}&role=${encodeURIComponent(role)}`,
        {
          method: "POST",
        }
      );

      const result = await response.json();
      if (response.ok) {
        showMessage(result.message, "success");
        signupForm.reset();
        fetchActivities();
      } else {
        showMessage(result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage("Failed to sign up. Please try again.", "error");
      console.error("Error signing up:", error);
    }
  });

  uploadForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const activity = uploadActivitySelect.value;
    const file = attendanceFileInput.files[0];
    if (!file) {
      showMessage("Please choose a CSV or Excel file.", "error");
      return;
    }

    const data = new FormData();
    data.append("file", file);

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/attendance/upload`,
        {
          method: "POST",
          body: data,
        }
      );

      const result = await response.json();
      if (response.ok) {
        showMessage(`${result.message}. Added: ${result.added}, Skipped: ${result.skipped}`, "success");
        uploadForm.reset();
        fetchActivities();
      } else {
        showMessage(result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage("Failed to upload attendance. Please try again.", "error");
      console.error("Error uploading attendance:", error);
    }
  });

  fetchActivities();
});
