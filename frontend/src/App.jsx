import Login from './components/Login'
import LoginScreen from './components/LoginScreen'
import { isAuthenticated } from './auth'
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from "react-router-dom";
import ErrorPage from "./components/ErrorPage.jsx";
import CustomerData from "./components/CustomerData.jsx";
import Agent from "./components/AgentScreen.jsx";
import AgentRoute from "./components/AgentRoute.jsx";
import AdminAdd from "./components/AdminAdd.jsx";
import AdminDash from "./components/AdminDash.jsx";
import AdminSearch from "./components/AdminSearch.jsx";
import AnalyticsPage from "./components/AnalyticsPage.jsx";
import OrganSearch from "./components/OrganSearch.jsx";

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
                   <Route path="/agent/:region" element={isAuthenticated() ? <AgentRoute /> : <LoginScreen />} />
                   <Route path="/adminadd" element={isAuthenticated() ? <AdminAdd /> : <LoginScreen />} />
                   <Route path="/admin" element={isAuthenticated() ? <AdminDash /> : <LoginScreen />} />
                   <Route path="/admin/search" element={isAuthenticated() ? <AdminSearch /> : <LoginScreen />} />
                   <Route path="/analytics" element={isAuthenticated() ? <AnalyticsPage /> : <LoginScreen />} />
                   <Route path="/organsearch" element={isAuthenticated() ? <OrganSearch /> : <LoginScreen />} />
                   <Route path="/airlogin" element={<LoginScreen />} />
                   {/*<Route path="/analytics" element={<Analytics />} />*/}

                   {/* Fallback route */}
                   <Route path="*" element={<ErrorPage />} />
               </Routes>
           </Router>
       </div>
   );
}

export default App
