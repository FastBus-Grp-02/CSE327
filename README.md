# FastBus Frontend

Modern, minimal, and aesthetic frontend pages for the FastBus ticket booking system.

## Pages

### 1. Login Page (`login.html`)
- **Route**: `/login`
- **Features**:
  - Email or username login
  - Password authentication
  - JWT token storage
  - Auto-redirect if already logged in
  - Loading states and error handling
  - Responsive design

### 2. Signup Page (`signup.html`)
- **Route**: `/signup`
- **Features**:
  - User registration form
  - Fields: First name, last name, email, username, password
  - Role selection (Customer/Admin)
  - Client-side validation
  - Password strength hints
  - Auto-redirect after registration
  - Responsive design

### 3. Trip Search Results (`search.html`)
- **Route**: `/trips/search`
- **Features**:
  - Search form with origin, destination, date, and seat count
  - Real-time filtering:
    - Price range filter
    - Seat class filter (Economy, Business, First Class)
    - Departure time filter (Morning, Afternoon, Evening, Night)
  - Sort options:
    - By departure time
    - By price
    - By duration
  - Trip cards displaying:
    - Route and times
    - Operator name
    - Duration
    - Vehicle type
    - Available seats
    - Price per seat
  - User profile and logout
  - Responsive design

## Design Features

- **Modern Gradient Design**: Purple gradient theme
- **Smooth Animations**: Fade-in, slide-in, and hover effects
- **Responsive Layout**: Works on desktop, tablet, and mobile
- **Clean Typography**: System fonts for optimal readability
- **Accessible**: High contrast, clear labels, focus states
- **Loading States**: Visual feedback for all async operations
- **Error Handling**: User-friendly error messages

## Setup

1. **Start the Backend**:
   ```bash
   cd d:/me/ticket-hub
   python run.py
   ```

2. **Open Frontend Pages**:
   - Simply open the HTML files in your browser
   - Or use a local server (recommended):
     ```bash
     cd frontend
     python -m http.server 8000
     ```
   - Then navigate to:
     - http://localhost:8000/login.html
     - http://localhost:8000/signup.html
     - http://localhost:8000/search.html

## API Configuration

The pages are configured to connect to:
```javascript
const API_BASE_URL = 'http://localhost:5000/api';
```

If your backend runs on a different port, update this variable in each HTML file.

## Authentication Flow

1. User signs up or logs in
2. JWT tokens are stored in localStorage:
   - `access_token`: For API requests
   - `refresh_token`: For token renewal
   - `user`: User profile data
3. Protected pages check for tokens
4. Tokens are automatically included in API requests

## Browser Compatibility

- Chrome/Edge: Full support
- Firefox: Full support
- Safari: Full support
- Mobile browsers: Full support

## Tech Stack

- **HTML5**: Semantic markup
- **CSS3**: Modern styling with Grid, Flexbox, animations
- **Vanilla JavaScript**: No dependencies, pure ES6+
- **Fetch API**: For backend communication

## Color Scheme

```css
--primary: #6366f1       /* Indigo */
--secondary: #8b5cf6     /* Purple */
--error: #ef4444         /* Red */
--success: #10b981       /* Green */
--text: #1f2937          /* Dark gray */
--text-light: #6b7280    /* Light gray */
```

## Future Enhancements

- Booking page with seat selection
- Payment integration
- User profile management
- Booking history
- Promo code application
- Trip details modal
- Real-time availability updates
- Push notifications

## Notes

- All pages are self-contained (HTML + CSS + JS in one file)
- No external dependencies required
- Images and icons can be added later
- CORS must be enabled on the backend for local testing

