import { createContext } from "react";

const loginContext = createContext({
    name: "", 
    islog: false, 
    email: "", 
    trial_active: false, 
    trial_end_date: ""
});

export default loginContext;