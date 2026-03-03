import { initializeApp } from "../lib/firebase-app-compat.js";
        import { getAuth, signInWithEmailAndPassword, createUserWithEmailAndPassword } from "../lib/firebase-auth-compat.js";
        import { getFirestore, doc, setDoc } from "../lib/firebase-firestore-compat.js";

        const firebaseConfig = {};

        const app = initializeApp(firebaseConfig);
        const auth = getAuth(app);
        const db = getFirestore(app);

        let isLoginMode = true;
        const form = document.getElementById('authForm');
        const statusMsg = document.getElementById('status-msg');

        document.getElementById('toggleBtn').addEventListener('click', (e) => {
            e.preventDefault();
            isLoginMode = !isLoginMode;
            updateUI();
        });

        function updateUI() {
            const nameField = document.getElementById('nameField');
            const roleField = document.getElementById('roleField');
            const formTitle = document.getElementById('formTitle');
            const submitBtn = document.getElementById('submitBtn');
            const toggleText = document.getElementById('toggleText');
            const toggleBtn = document.getElementById('toggleBtn');

            if (isLoginMode) {
                nameField.classList.add('hidden');
                roleField.classList.add('hidden');
                formTitle.textContent = "Welcome back, Sir.";
                submitBtn.textContent = "Sign In";
                toggleText.innerHTML = 'New here? <a href="#" id="toggleBtn" class="text-primary text-decoration-none fw-bold">Create Account</a>';
            } else {
                nameField.classList.remove('hidden');
                roleField.classList.remove('hidden');
                formTitle.textContent = "Create your Academic ID";
                submitBtn.textContent = "Sign Up";
                toggleText.innerHTML = 'Already have an account? <a href="#" id="toggleBtn" class="text-primary text-decoration-none fw-bold">Login</a>';
            }
            document.getElementById('toggleBtn').addEventListener('click', (e) => {
                e.preventDefault();
                isLoginMode = !isLoginMode;
                updateUI();
            });
            statusMsg.classList.add('d-none');
        }

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const fullName = document.getElementById('fullName').value;
            const role = document.getElementById('role').value;

            statusMsg.classList.remove('d-none', 'alert-danger', 'alert-success');
            statusMsg.classList.add('alert-info');
            statusMsg.textContent = isLoginMode ? "Authenticating..." : "Creating Account...";

            try {
                if (isLoginMode) {
                    const userCredential = await signInWithEmailAndPassword(auth, email, password);
                    statusMsg.classList.replace('alert-info', 'alert-success');
                    statusMsg.textContent = "Login Successful! Redirecting...";
                    setTimeout(() => window.location.href = "index.html", 1000);
                } 
                else {
                    if (!fullName) throw new Error("Please enter your full name.");

                    const userCredential = await createUserWithEmailAndPassword(auth, email, password, {
                        name: fullName,
                        role
                    });
                    const user = userCredential.user;

                    await setDoc(doc(db, "users", user.uid), {
                        name: fullName,
                        email: email,
                        role: role,
                        createdAt: new Date()
                    });

                    statusMsg.classList.replace('alert-info', 'alert-success');
                    statusMsg.textContent = "Account Created! Redirecting...";
                    setTimeout(() => window.location.href = "index.html", 1500);
                }
            } catch (error) {
                console.error(error);
                statusMsg.classList.replace('alert-info', 'alert-danger');
                statusMsg.textContent = formatErrorMessage(error.message);
            }
        });

        function formatErrorMessage(msg) {
            if (msg.includes("Email already exists")) return "Email is already registered.";
            if (msg.includes("Invalid credentials")) return "Invalid Email or Password.";
            if (msg.includes("auth/email-already-in-use")) return "Email is already registered.";
            if (msg.includes("auth/weak-password")) return "Password should be at least 6 characters.";
            if (msg.includes("auth/invalid-credential")) return "Invalid Email or Password.";
            return msg;
        }

async function loginUser(event) {
    event.preventDefault(); 

    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    try {
        const response = await fetch("http://127.0.0.1:8000/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                email: email,
                password: password
            })
        });

        const data = await response.json();

        if (response.ok) {
            alert("Login successful!");
            console.log(data);

            localStorage.setItem("token", data.access_token);

            window.location.href = "dashboard.html";
        } else {
            alert(data.detail || "Login failed");
        }

    } catch (error) {
        console.error("Error:", error);
        alert("Server error");
    }
}
