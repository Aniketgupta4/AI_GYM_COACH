from core.base_exercise import BaseExercise


class ShoulderPressDetector(BaseExercise):
    UP_THRESHOLD = 140
    DOWN_THRESHOLD = 100
    MIN_VISIBILITY = 0.40

    LEFT_SHOULDER = 11
    LEFT_ELBOW = 13
    LEFT_WRIST = 15
    RIGHT_SHOULDER = 12
    RIGHT_ELBOW = 14
    RIGHT_WRIST = 16
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26

    def __init__(self):
        super().__init__()

    def reset(self) -> None:
        self.reps = 0
        self.stage = None

    def process(self, landmarks) -> dict:
        left_angle = self.calculate_angle(
            self.get_point(landmarks, self.LEFT_SHOULDER),
            self.get_point(landmarks, self.LEFT_ELBOW),
            self.get_point(landmarks, self.LEFT_WRIST),
        )
        right_angle = self.calculate_angle(
            self.get_point(landmarks, self.RIGHT_SHOULDER),
            self.get_point(landmarks, self.RIGHT_ELBOW),
            self.get_point(landmarks, self.RIGHT_WRIST),
        )

        left_vis = min(
            landmarks[self.LEFT_SHOULDER].visibility,
            landmarks[self.LEFT_ELBOW].visibility,
            landmarks[self.LEFT_WRIST].visibility,
        )
        right_vis = min(
            landmarks[self.RIGHT_SHOULDER].visibility,
            landmarks[self.RIGHT_ELBOW].visibility,
            landmarks[self.RIGHT_WRIST].visibility,
        )

        left_visible = left_vis >= self.MIN_VISIBILITY
        right_visible = right_vis >= self.MIN_VISIBILITY

        if left_visible and right_visible:
            elbow_angle = (left_angle + right_angle) / 2.0
            key_landmarks_visible = True
            primary_shoulder = self.LEFT_SHOULDER if left_vis >= right_vis else self.RIGHT_SHOULDER
            primary_hip = self.LEFT_HIP if left_vis >= right_vis else self.RIGHT_HIP
            primary_knee = self.LEFT_KNEE if left_vis >= right_vis else self.RIGHT_KNEE
        elif left_visible:
            elbow_angle = left_angle
            key_landmarks_visible = True
            primary_shoulder = self.LEFT_SHOULDER
            primary_hip = self.LEFT_HIP
            primary_knee = self.LEFT_KNEE
        elif right_visible:
            elbow_angle = right_angle
            key_landmarks_visible = True
            primary_shoulder = self.RIGHT_SHOULDER
            primary_hip = self.RIGHT_HIP
            primary_knee = self.RIGHT_KNEE
        else:
            elbow_angle = left_angle
            key_landmarks_visible = False
            primary_shoulder = self.LEFT_SHOULDER
            primary_hip = self.LEFT_HIP
            primary_knee = self.LEFT_KNEE

        if key_landmarks_visible:
            if elbow_angle > self.UP_THRESHOLD:
                self.stage = "up"

            if elbow_angle < self.DOWN_THRESHOLD and self.stage == "up":
                self.stage = "down"
                self.reps += 1

        if elbow_angle >= self.UP_THRESHOLD:
            extension_status = "FULL EXTENSION"
        elif elbow_angle >= 120:
            extension_status = "NEARLY EXTENDED"
        elif elbow_angle >= self.DOWN_THRESHOLD:
            extension_status = "PRESSING"
        else:
            extension_status = "START POSITION"

        # Robust back arch calculation (safe when user is sitting and knees are out of frame)
        hip_vis = max(landmarks[self.LEFT_HIP].visibility, landmarks[self.RIGHT_HIP].visibility)
        knee_vis = max(landmarks[self.LEFT_KNEE].visibility, landmarks[self.RIGHT_KNEE].visibility)

        if hip_vis >= self.MIN_VISIBILITY and knee_vis >= self.MIN_VISIBILITY:
            back_angle = self.calculate_angle(
                self.get_point(landmarks, primary_shoulder),
                self.get_point(landmarks, primary_hip),
                self.get_point(landmarks, primary_knee),
            )
            if back_angle >= 155:
                back_arch_status = "Neutral"
            elif back_angle >= 135:
                back_arch_status = "Slight Arch"
            else:
                back_arch_status = "Excessive Arch"
        else:
            back_arch_status = "Neutral"

        return {
            "reps": self.reps,
            "elbow_angle": int(elbow_angle),
            "extension_status": extension_status,
            "back_arch_status": back_arch_status,
        }
