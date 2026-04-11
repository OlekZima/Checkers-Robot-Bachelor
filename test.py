import cv2 as cv


def main() -> None:
    cap = cv.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        cv.imshow("Camera Feed", frame)
        if cv.waitKey(1) & 0xFF == ord("q"):
            break
    cap.release()
    cv.destroyAllWindows()


if __name__ == "__main__":
    main()
