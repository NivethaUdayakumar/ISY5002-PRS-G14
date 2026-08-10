import { useState } from 'react'
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
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App
