import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from './assets/vite.svg'
import heroImg from './assets/hero.png'
import './App.css'
import MainLayout from './layouts/main_layout'
import CameraPage from './pages/camera_page'
import {
  BrowserRouter,
  Routes,
  Route,
} from "react-router-dom";


function App() {
  const [count, setCount] = useState(0)

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<MainLayout />}>
          <Route path="/" element={<CameraPage />} />
          {/* <Route path="/about" element={<About />} />
          <Route path="/profile" element={<Profile />} /> */}
        </Route>

      </Routes>
    </BrowserRouter>
  );
}

export default App
