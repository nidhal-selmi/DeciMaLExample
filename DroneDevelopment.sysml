package DroneLogicalArchitecture {
    part def LogicalFunction {
        attribute description : String
    }
    part def LogicalComponent;
    part def LogicalActor;

    // Logical Actors (unchanged)
    part DroneOperator : LogicalActor;
    part AirlineDataBase : LogicalActor;
    part AirTrafficManagement : LogicalActor;
    part DroneEnvironment : LogicalActor;
    part Aircraft : LogicalActor;

    // All components are defined as LogicalComponents
    part AIDA : LogicalComponent {
        part Drone : LogicalComponent {
            part FlightControl : LogicalComponent;
            part PropulsionSystem : LogicalComponent;
            part Structure : LogicalComponent;
            part Payload : LogicalComponent;
        }
        part RemoteControl : LogicalComponent;
        part ControlDesk : LogicalComponent;
    }

    part Drone : LogicalComponent {
        part PropulsionSystem : LogicalComponent {
            // (Empty block)
        }
        part ControlSystem : LogicalComponent {
            part FlightController : LogicalComponent;
            part Sensors : LogicalComponent {
                part GPS : LogicalComponent;
                part IMU : LogicalComponent;
                part Barometer : LogicalComponent;
            }
        }
        part PowerSystem : LogicalComponent {
            part Battery : LogicalComponent;
        }
        part Frame : LogicalComponent {
            part Arms[4] : LogicalComponent;
            part Body : LogicalComponent;
        }
    }

    // Define a package for functions, keeping only the LogFun_X functions
    package DroneFunctions {
        part LogFun_1 : LogicalFunction {
            description = "Provide direct remote identification information"
        }
        part LogFun_2 : LogicalFunction {
            description = "Manage mission"
        }
        part LogFun_3 : LogicalFunction {
            description = "Sense drone state and environment"
        }
        part LogFun_4 : LogicalFunction {
            description = "Control drone motion"
        }
        part LogFun_5 : LogicalFunction {
            description = "Acquire visual information"
        }
        part LogFun_6 : LogicalFunction {
            description = "Detect AIDA failures"
        }
        part LogFun_7 : LogicalFunction {
            description = "Analyse acquired visual information"
        }
    }
}
