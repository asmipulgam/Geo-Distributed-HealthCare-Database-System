import { useMemo, useState } from 'react'
import '../login.css'
import axios from "axios";
import { useNavigate } from "react-router-dom";

function isDigits(str) {
  return /^\d+$/.test(str)
}

function parseYYYYMMDD(str) {
  // Accepts YYYY-MM-DD strictly
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(str)
  if (!m) return null
  const [_, y, mo, d] = m
  const year = Number(y)
  const monthIndex = Number(mo) - 1
  const day = Number(d)
  const dt = new Date(Date.UTC(year, monthIndex, day))
  // Basic sanity: month/day preserved
  if (
    dt.getUTCFullYear() !== year ||
    dt.getUTCMonth() !== monthIndex ||
    dt.getUTCDate() !== day
  ) {
    return null
  }
  return dt
}


export default function Login() {
  const [step, setStep] = useState(1)
    const [userData, setUserData] = useState({});
  const [isLoading, setIsLoading] = useState(false);
    const navigate = useNavigate();

  // Step 1: Health ID
  const [healthId, setHealthId] = useState('')
  const [healthIdTouched, setHealthIdTouched] = useState(false)
  const healthIdError = useMemo(() => {
    if (!healthId) return 'Health ID is required'
    if (!isDigits(healthId)) return 'Health ID must be numeric'
    if (healthId.length < 6) return 'Health ID must be at least 6 digits'
    return null
  }, [healthId])

  const US_STATES = {
    'AL': 'Alabama',
    'AK': 'Alaska',
    'AZ': 'Arizona',
    'AR': 'Arkansas',
    'CA': 'California',
    'CO': 'Colorado',
    'CT': 'Connecticut',
    'DE': 'Delaware',
    'FL': 'Florida',
    'GA': 'Georgia',
    'HI': 'Hawaii',
    'ID': 'Idaho',
    'IL': 'Illinois',
    'IN': 'Indiana',
    'IA': 'Iowa',
    'KS': 'Kansas',
    'KY': 'Kentucky',
    'LA': 'Louisiana',
    'ME': 'Maine',
    'MD': 'Maryland',
    'MA': 'Massachusetts',
    'MI': 'Michigan',
    'MN': 'Minnesota',
    'MS': 'Mississippi',
    'MO': 'Missouri',
    'MT': 'Montana',
    'NE': 'Nebraska',
    'NV': 'Nevada',
    'NH': 'New Hampshire',
    'NJ': 'New Jersey',
    'NM': 'New Mexico',
    'NY': 'New York',
    'NC': 'North Carolina',
    'ND': 'North Dakota',
    'OH': 'Ohio',
    'OK': 'Oklahoma',
    'OR': 'Oregon',
    'PA': 'Pennsylvania',
    'RI': 'Rhode Island',
    'SC': 'South Carolina',
    'SD': 'South Dakota',
    'TN': 'Tennessee',
    'TX': 'Texas',
    'UT': 'Utah',
    'VT': 'Vermont',
    'VA': 'Virginia',
    'WA': 'Washington',
    'WV': 'West Virginia',
    'WI': 'Wisconsin',
    'WY': 'Wyoming'
  };

  const [state, setState] = useState('')
  const [stateTouched, setStateTouched] = useState(false)
  const stateError = useMemo(() => {
    if (!state) return 'State is required'
    if (!US_STATES[state]) return 'Invalid state selected'
    return null
  }, [state])

    const fetchUserDetails = (id) => {
        setIsLoading(true);
        axios.post("BACKEND/getcustomer",{
            id: id
        }).then(res => {
            setUserData(res.data)
            setIsLoading(false)
            setStep(2)
        }).catch(err => {console.log(err)})

    }

  // Step 2: DOB
  const [dobMode, setDobMode] = useState('calendar') // 'calendar' | 'manual'
  const [dobCalendar, setDobCalendar] = useState('') // YYYY-MM-DD from <input type="date">
  const [dobManual, setDobManual] = useState('') // YYYY-MM-DD as text
  const [dobTouched, setDobTouched] = useState(false)

  const parsedDob = useMemo(() => {
    const value = dobMode === 'calendar' ? dobCalendar : dobManual
    const parsed = parseYYYYMMDD(value)
    return parsed
  }, [dobMode, dobCalendar, dobManual])

  const dobError = useMemo(() => {
    const value = dobMode === 'calendar' ? dobCalendar : dobManual
    if (!value) return 'Date of birth is required'
    const parsed = parseYYYYMMDD(value)
    if (!parsed) return 'Enter date as YYYY-MM-DD'
    const today = new Date()
    const todayUTC = new Date(Date.UTC(today.getFullYear(), today.getMonth(), today.getDate()))
    if (parsed > todayUTC) return 'Date of birth cannot be in the future'
    return null
  }, [dobMode, dobCalendar, dobManual])

  const [submitted, setSubmitted] = useState(false)

  function handleNext() {
    setHealthIdTouched(true)
    if (!healthIdError) {
      //setStep(2)
        fetchUserDetails(healthId)
    }
  }

  function handleLogin(e) {
    e.preventDefault()
    setDobTouched(true)
    if (!dobError && parsedDob) {
      setSubmitted(true)
        navigate("/details", { state: { user: userData } });

    }
  }

  if (submitted) {
    return (
      <div className="login-container">
        <div className="login-card">
          <h1 className="login-title">Logged in</h1>
          <p className="login-success">Health ID: <strong>{healthId}</strong></p>
          <p className="login-success">DOB: <strong>{parsedDob?.toISOString().slice(0, 10)}</strong></p>
        </div>
      </div>
    )
  }

  return (
    <div className="login-container">
      <div className="login-card">
        <h1 className="login-title">Welcome</h1>
        {step === 1 && (
          <div className="step">
            <h2 className="step-title">Enter Health ID</h2>
            <label className="field">
              <span className="field-label">Health ID</span>
              <input
                className="input"
                type="text"
                inputMode="numeric"
                pattern="\\d*"
                placeholder="e.g., 123456"
                value={healthId}
                onChange={(e) => setHealthId(e.target.value.trim())}
                onBlur={() => setHealthIdTouched(true)}
                aria-invalid={!!(healthIdTouched && healthIdError)}
                aria-describedby="health-id-error"
              />
            </label>
            {healthIdTouched && healthIdError && (
              <div id="health-id-error" className="error">{healthIdError}</div>
            )}
            <label className="field">
              <span className="field-label">State</span>
              <select
                className="input"
                value={state}
                onChange={(e) => setState(e.target.value)}
                onBlur={() => setStateTouched(true)}
                aria-invalid={!!(stateTouched && stateError)}
                aria-describedby="state-error"
              >
                <option value="">Select a state</option>
                {Object.entries(US_STATES).map(([abbreviation, name]) => (
                  <option key={abbreviation} value={abbreviation}>
                    {name}
                  </option>
                ))}
              </select>
            </label>
            {stateTouched && stateError && (
              <div id="state-error" className="error">{stateError}</div>
            )}
            <div className="actions">
              <button className="btn primary" onClick={handleNext} disabled={!!healthIdError && !!isLoading}>
                Next
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <form className="step" onSubmit={handleLogin}>
            <h2 className="step-title">Confirm Date of Birth</h2>
            <div className="segmented">
              <button
                type="button"
                className={`segmented-item ${dobMode === 'calendar' ? 'active' : ''}`}
                onClick={() => setDobMode('calendar')}
              >
                Calendar
              </button>
            </div>

            {dobMode === 'calendar' ? (
              <label className="field">
                <span className="field-label">Date of birth</span>
                <input
                  className="input"
                  type="date"
                  placeholder="YYYY-MM-DD"
                  value={dobCalendar}
                  onChange={(e) => setDobCalendar(e.target.value)}
                  onBlur={() => setDobTouched(true)}
                  aria-invalid={!!(dobTouched && dobError)}
                  aria-describedby="dob-error"
                  max={new Date().toISOString().slice(0, 10)}
                />
              </label>
            ) : (
              <label className="field">
                <span className="field-label">Date of birth (YYYY-MM-DD)</span>
                <input
                  className="input"
                  type="text"
                  inputMode="numeric"
                  placeholder="YYYY-MM-DD"
                  value={dobManual}
                  onChange={(e) => setDobManual(e.target.value)}
                  onBlur={() => setDobTouched(true)}
                  aria-invalid={!!(dobTouched && dobError)}
                  aria-describedby="dob-error"
                />
              </label>
            )}

            {dobTouched && dobError && (
              <div id="dob-error" className="error">{dobError}</div>
            )}

            <div className="actions">
              <button type="button" className="btn" onClick={() => setStep(1)}>
                Back
              </button>
              <button type="submit" className="btn primary" disabled={!!dobError}>
                Log in
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}