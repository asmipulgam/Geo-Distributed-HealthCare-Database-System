import Login from './components/Login'
import { BrowserRouter as Router, Routes, Route, Link, useParams, Navigate } from "react-router-dom";
import ErrorPage from "./components/ErrorPage.jsx";
import CustomerData from "./components/CustomerData.jsx";
import Agent from "./components/AgentScreen.jsx";
import Admin from "./components/Admin.jsx";

function App() {

   return(
       <div style={{width: "100vw", height: "100vh", alignItems: "center"}}>

           <Router>
               <Routes>
                   {/* Default route redirects to /login */}
                   <Route path="/" element={<Navigate to="/login" replace />} />

                   {/* Actual routes */}
                   <Route path="/login" element={<Login />} />
                   <Route path="/customerdetails" element={<CustomerData />} />
                   <Route path="/agent/:region" element={<Agent />} />
                   <Route path="/admin" element={<Admin />} />
                   {/*<Route path="/analytics" element={<Analytics />} />*/}

                   {/* Fallback route */}
                   <Route path="*" element={<ErrorPage />} />
               </Routes>
           </Router>
       </div>
   );
}

export default App
