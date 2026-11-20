from core.base_exercise import BaseExercise


class SquatDetector(BaseExercise):
    DOWN_THRESHOLD = 110   
    UP_THRESHOLD = 150     
    MIN_VISIBILITY = 0.40

    LEFT_HIP = 23
    LEFT_KNEE = 25
    LEFT_ANKLE = 27
    RIGHT_HIP = 24
    RIGHT_KNEE = 26
    RIGHT_ANKLE = 28
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12

    def __init__(self):
        super().__init__()
        self.min_knee_angle = 180
        self.shallow_flag = False

    def reset(self):
        self.reps = 0
        self.stage = None
        self.min_knee_angle = 180
        self.shallow_flag = False

    def process(self, landmarks):
        left_knee_angle = self.calculate_angle(
            self.get_point(landmarks, self.LEFT_HIP),
            self.get_point(landmarks, self.LEFT_KNEE),
            self.get_point(landmarks, self.LEFT_ANKLE)
        )

        right_knee_angle = self.calculate_angle(
            self.get_point(landmarks, self.RIGHT_HIP),
            self.get_point(landmarks, self.RIGHT_KNEE),
            self.get_point(landmarks, self.RIGHT_ANKLE)
        )

        left_vis = landmarks[self.LEFT_KNEE].visibility
        right_vis = landmarks[self.RIGHT_KNEE].visibility

        if left_vis >= right_vis:
            knee_angle = left_knee_angle
            hip_idx, knee_idx, shoulder_idx = self.LEFT_HIP, self.LEFT_KNEE, self.LEFT_SHOULDER
        else:
            knee_angle = right_knee_angle
            hip_idx, knee_idx, shoulder_idx = self.RIGHT_HIP, self.RIGHT_KNEE, self.RIGHT_SHOULDER

        back_angle = self.calculate_angle(
            self.get_point(landmarks, shoulder_idx),
            self.get_point(landmarks, hip_idx),
            self.get_point(landmarks, knee_idx)
        )

        key_landmark_visible = (
            landmarks[hip_idx].visibility >= self.MIN_VISIBILITY
            and landmarks[knee_idx].visibility >= self.MIN_VISIBILITY
        )

        if key_landmark_visible:
            if knee_angle < self.min_knee_angle:
                self.min_knee_angle = knee_angle

            if knee_angle < self.DOWN_THRESHOLD:
                self.stage = "down"

            if knee_angle >= self.UP_THRESHOLD:
                if self.stage == "down":
                    self.stage = "up"
                    self.reps += 1
                    self.min_knee_angle = 180
                    self.shallow_flag = False
                elif self.min_knee_angle < 135:
                    self.shallow_flag = True
                    self.min_knee_angle = 180

        if self.shallow_flag:
            depth_status = "TOO SHALLOW"
        elif self.stage == "down" or knee_angle <= self.DOWN_THRESHOLD:
            depth_status = "GOOD DEPTH"
        elif knee_angle < 135:
            depth_status = "SQUATTING"
        else:
            depth_status = "STANDING"

        return {
            "reps": self.reps,
            "knee_angle": int(knee_angle),
            "back_angle": int(back_angle),
            "depth_status": depth_status
        }
